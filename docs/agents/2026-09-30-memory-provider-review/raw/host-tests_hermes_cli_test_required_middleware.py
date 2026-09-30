# ABOUTME: Verifies that required middleware stops execution when its check fails.
# ABOUTME: Preserves optional failure behavior and single-use downstream execution.
import logging
import pytest
from hermes_cli.plugins import PluginContext, PluginManifest, get_plugin_manager
from hermes_cli.middleware import run_llm_execution_middleware

@pytest.fixture
def context(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "profile"))
    manager = get_plugin_manager()
    manager.discover_and_load()
    ctx = PluginContext(PluginManifest(name="required-test", version="1.0.0", description="Test"), manager)
    yield ctx, manager
    manager.unload()

def fail(**kwargs):
    raise ValueError("test policy failure")

@pytest.mark.parametrize("kind", ["llm_request", "tool_request"])
def test_required_request_failure_propagates(context, kind, caplog):
    ctx, manager = context
    ctx.register_middleware(kind, fail, required=True)
    with caplog.at_level(logging.WARNING), pytest.raises(ValueError, match="test policy failure"):
        manager.invoke_middleware(kind, request={})
    assert "test policy failure" in caplog.text

def test_optional_request_failure_remains_isolated(context, caplog):
    ctx, manager = context
    ctx.register_middleware("llm_request", fail)
    ctx.register_middleware("llm_request", lambda **kw: {"request": {"allowed": True}})
    with caplog.at_level(logging.WARNING):
        assert manager.invoke_middleware("llm_request", request={}) == [{"request": {"allowed": True}}]
    assert "test policy failure" in caplog.text

@pytest.mark.parametrize("required", [False, True])
def test_execution_failure_before_downstream(context, required, caplog):
    ctx, _ = context
    ctx.register_middleware("llm_execution", fail, required=required)
    called = []
    def terminal(request):
        called.append(request)
        return "response"
    with caplog.at_level(logging.WARNING):
        if required:
            with pytest.raises(ValueError, match="test policy failure"):
                run_llm_execution_middleware({"messages": []}, terminal)
            assert called == []
        else:
            assert run_llm_execution_middleware({"messages": []}, terminal) == "response"
            assert len(called) == 1
    assert "test policy failure" in caplog.text

def test_required_failure_after_downstream_does_not_repeat(context, caplog):
    ctx, _ = context
    def after(next_call, request, **kwargs):
        next_call(request)
        raise ValueError("test policy failure")
    ctx.register_middleware("llm_execution", after, required=True)
    called = []
    with caplog.at_level(logging.WARNING), pytest.raises(ValueError, match="test policy failure"):
        run_llm_execution_middleware({}, lambda request: called.append(request))
    assert called == [{}]
    assert "test policy failure" in caplog.text

def test_required_registration_disposes(context):
    ctx, manager = context
    lease = ctx.register_middleware("llm_execution", fail, required=True)
    assert manager.has_middleware("llm_execution")
    lease.dispose()
    assert not manager.has_middleware("llm_execution")

@pytest.mark.parametrize("asynchronous", [False, True])
def test_required_admission_blocks_auxiliary_attempt(context, asynchronous, caplog):
    import asyncio
    from types import SimpleNamespace
    from agent.auxiliary_hooks import run_with_aux_hooks, arun_with_aux_hooks
    ctx, _ = context
    ctx.register_middleware("llm_admission", fail, required=True)
    called = []
    metadata = dict(aux_task="compression", metadata={}, client=SimpleNamespace(base_url="http://127.0.0.1/v1"),
                    kwargs={"model": "synthetic-model", "messages": []}, provider="synthetic", model="synthetic-model", api_mode="chat_completions")
    async def async_terminal():
        called.append(True)
    with caplog.at_level(logging.WARNING), pytest.raises(ValueError, match="test policy failure"):
        if asynchronous:
            asyncio.run(arun_with_aux_hooks(async_terminal, **metadata))
        else:
            run_with_aux_hooks(lambda: called.append(True), **metadata)
    assert called == []
    assert "test policy failure" in caplog.text

def test_required_admission_blocks_primary_attempt(context, caplog):
    ctx, _ = context
    ctx.register_middleware("llm_admission", fail, required=True)
    called = []
    with caplog.at_level(logging.WARNING), pytest.raises(ValueError, match="test policy failure"):
        run_llm_execution_middleware({}, lambda request: called.append(request))
    assert called == []
