"""The guide's MCP surface: shared state across routes, skills and change notices."""

import asyncio
import hashlib

import pytest
from fastmcp import Client
from fastmcp.skills import SkillsClientExtension
from fastmcp.skills.extension import SkillsExtension
from fastmcp.skills.models import (
    GetSkillParams,
    GetSkillRequest,
    GetSkillResult,
    ListSkillsParams,
    ListSkillsRequest,
    ListSkillsResult,
)
from mcp.types import ResourceListChangedNotification

import synapse_showcase.skills
from synapse_showcase.guide import Guide
from synapse_showcase.loopback import create_http_app
from synapse_showcase.state import GuideStore
from tests.conftest import PROJECT_ROOT, call, eventually, over_http, serve, state, tool_names

SKILLS_EXTENSION = "io.modelcontextprotocol/skills"
# NimbleBrain negotiates 2025-11-25 through the initialize handshake today; a modern client
# discovers the sessionless 2026-07-28 era. Skills must answer on both.
ERAS = [("legacy", "2025-11-25"), ("auto", "2026-07-28")]


async def test_native_and_external_tools_share_saved_state_across_a_restart(data_file):
    async with serve(create_http_app(Guide(GuideStore(data_file)))) as base:
        async with over_http(base) as native, over_http(base, "/agent/mcp") as agent:
            assert "guide_connection_check" not in await tool_names(native)
            assert "guide_connection_check" in await tool_names(agent)
            await state(native, "guide_step", {"step": "board"})
            created = await state(agent, "board_add", {"title": "A shared sample"})
            card = created["cards"][-1]
            await state(native, "board_move", {"id": card["id"], "status": "doing"})
            saved = data_file.read_bytes()
            await state(native, "board_move", {"id": card["id"], "status": "doing"})
            assert data_file.read_bytes() == saved, "a move to the same column rewrites nothing"
            assert (await state(agent, "guide_status"))["cards"][-1]["status"] == "doing"

    async with Client(Guide(GuideStore(data_file)).make_server()) as reopened:
        current = await state(reopened, "guide_status")
    assert current["step"] == "board"
    assert current["cards"][-1]["title"] == "A shared sample"
    assert current["cards"][-1]["status"] == "doing"
    assert current["revision"] == 3


async def test_only_the_external_connection_check_completes_the_agents_chapter(data_file):
    async with serve(create_http_app(Guide(GuideStore(data_file)))) as base:
        async with over_http(base) as native, over_http(base, "/agent/mcp") as agent:
            refused = await call(native, "guide_step", {"step": "agents", "complete": True})
            assert refused.is_error
            chosen = await state(native, "guide_step", {"step": "agents"})
            assert chosen["step"] == "agents"
            assert "agents" not in chosen["completed"]
            checked = await state(agent, "guide_connection_check")
            assert "agents" in checked["completed"]
            assert "agentCheck" in checked


async def test_unreadable_progress_is_a_tool_error_and_stays_on_disk(data_file):
    data_file.parent.mkdir(parents=True)
    data_file.write_text("interrupted personal progress")
    async with Client(Guide(GuideStore(data_file)).make_server()) as client:
        result = await call(client, "guide_status")
        assert result.is_error
        assert "could not be read" in result.content[0].text
        assert (await call(client, "board_add", {"title": "Not over it"})).is_error
    assert data_file.read_text() == "interrupted personal progress"


async def test_arguments_are_checked_against_the_listed_schema(data_file):
    async with Client(Guide(GuideStore(data_file)).make_server()) as client:
        refused = await call(client, "guide_step", {"step": "body"})
        assert refused.is_error
        assert refused.content[0].text.startswith(
            "Input validation error: Invalid arguments for tool guide_step: step:"
        )
        assert (await call(client, "guide_view", {"zoom": 2})).is_error
        assert (await call(client, "board_add", {})).is_error
        assert not data_file.exists()

        await state(client, "guide_view", {"focus": "agent", "zoom": 1.2})
        paused = await state(client, "guide_view", {"playing": True, "ignored": "x"})
        assert paused["view"] == {"zoom": 1.2, "playing": True, "focus": "agent"}
        cleared = await state(client, "guide_view", {"focus": None})
        assert cleared["view"] == {"zoom": 1.2, "playing": True, "focus": None}


@pytest.mark.parametrize(("mode", "protocol"), ERAS)
async def test_the_skills_are_listed_and_fetched_on_both_protocol_eras(data_file, mode, protocol):
    server = Guide(GuideStore(data_file)).make_server()
    async with Client(server, mode=mode, extensions=[SkillsClientExtension()]) as client:
        assert client.protocol_version == protocol
        if mode == "auto":
            assert SKILLS_EXTENSION in client.server_capabilities.extensions
            listing = await client.list_skills()
            fetch = client.get_skill
        else:
            # The SDK strips capabilities.extensions from a handshake-era initialize result and
            # FastMCP's client helpers refuse that era, so a 2025-11-25 host sends the methods
            # itself, as the host did against the old shim.
            listed = await client.session.send_request(
                ListSkillsRequest(params=ListSkillsParams()), ListSkillsResult
            )
            assert listed.result_type == "complete"
            listing = listed.skills

            async def fetch(uri):
                request = GetSkillRequest(params=GetSkillParams(uri=uri))
                return (await client.session.send_request(request, GetSkillResult)).skill

        assert [skill.uri for skill in listing] == [
            "skill://showcase-add-app/SKILL.md",
            "skill://showcase-guide/SKILL.md",
        ]
        for skill in listing:
            folder = skill.uri.split("/")[-2]
            assert skill.frontmatter.name == folder
            assert skill.frontmatter.description
            assert await fetch(skill.uri) == skill
            contents = (await client.read_resource_mcp(skill.uri)).contents[0]
            assert contents.mime_type == "text/markdown"
            served = contents.text.encode()
            assert served == (PROJECT_ROOT / "skills" / folder / "SKILL.md").read_bytes()
            assert [resource.model_dump() for resource in skill.resources] == [
                {
                    "uri": skill.uri,
                    "digest": f"sha256:{hashlib.sha256(served).hexdigest()}",
                    "size": len(served),
                }
            ]
    assert not data_file.exists()


def test_skills_come_from_fastmcps_extension_with_the_era_limit_lifted(data_file):
    extension = Guide(GuideStore(data_file)).make_server()._extensions[SKILLS_EXTENSION]
    assert isinstance(extension, SkillsExtension)
    assert {binding.method: binding.protocol_versions for binding in extension.methods()} == {
        "skills/list": None,
        "skills/get": None,
    }
    # The mcp 1.x request-union shim is gone: the module defines no request or result models.
    assert not [
        name for name in dir(synapse_showcase.skills) if name.endswith(("Request", "Result"))
    ]


async def test_persisted_writes_announce_a_change_and_reads_do_not(data_file):
    guide = Guide(GuideStore(data_file))
    notices: list[None] = []
    guide.listeners.add(lambda: notices.append(None))
    announced: list[ResourceListChangedNotification] = []

    async def receive(message):
        if isinstance(message, ResourceListChangedNotification):
            announced.append(message)

    # A change notice needs a standing session, so the native view speaks the handshake era the
    # NimbleBrain host negotiates; a sessionless 2026-07-28 connection has no channel for it.
    async with (
        Client(guide.make_server(), mode="legacy", message_handler=receive) as native,
        Client(guide.make_server(external=True)) as agent,
    ):
        await state(native, "guide_status")
        await asyncio.sleep(0.3)
        assert notices == []
        await state(agent, "board_add", {"title": "Agent notification sample"})
        await eventually(lambda: notices and announced, timeout=1)
        assert len(notices) == 1
        assert len(announced) == 1, "the native view hears about the agent's write"
        await state(native, "guide_status")
        await state(native, "catalog_list")
        await asyncio.sleep(0.3)
        assert len(notices) == 1


async def test_a_handshake_era_http_session_hears_an_agent_write_on_its_standing_stream(
    data_file,
):
    announced: list[ResourceListChangedNotification] = []

    async def receive(message):
        if isinstance(message, ResourceListChangedNotification):
            announced.append(message)

    # Over streamable HTTP the handshake era keeps a session id and a standing GET stream, the
    # channel the guide's notice travels on between requests.
    async with serve(create_http_app(Guide(GuideStore(data_file)))) as base:
        async with (
            over_http(base, mode="legacy", message_handler=receive) as native,
            over_http(base, "/agent/mcp") as agent,
        ):
            assert native.protocol_version == "2025-11-25"
            await state(native, "guide_status")
            await asyncio.sleep(0.3)
            assert announced == []
            await state(agent, "board_add", {"title": "Agent notification over HTTP"})
            await eventually(lambda: announced, timeout=2)
            await asyncio.sleep(0.3)
            assert len(announced) == 1, "exactly one notice for one write"


async def test_the_module_server_saves_progress_in_the_mpak_workspace(server_module, tmp_path):
    async with Client(server_module.mcp) as client:
        await state(client, "board_add", {"title": "Saved in the workspace"})
    saved = GuideStore(tmp_path / "workspace" / "showcase" / "progress.json").read()
    assert saved["cards"][-1]["title"] == "Saved in the workspace"
