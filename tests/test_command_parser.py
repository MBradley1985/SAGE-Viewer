"""Console command parser — behaviour regressions.

Guards against env-class commands leaking into the wrong flags (e.g. "show only
clusters" leaving pairs on) and against documented forms not matching.
"""

from visage.utils.command_parser import CommandContext, execute_command

ENV = (
    "env_show_field",
    "env_show_isolated",
    "env_show_group",
    "env_show_cluster",
    "env_show_pairs",
)


class _State:
    def __init__(self, env_on=True):
        for k in ENV:
            setattr(self, k, env_on)
        self.filter_gal_type = "both"

    def flush(self):
        pass


class _Ctrl:
    def __getattr__(self, name):
        return lambda *a, **k: None


def _run(cmd, env_on=True):
    s = _State(env_on=env_on)
    execute_command(cmd, CommandContext(scene=None, state=s, ctrl=_Ctrl()))
    return s


def _env(s):
    return {k.replace("env_show_", ""): getattr(s, k) for k in ENV}


def test_show_only_clusters_turns_everything_else_off():
    # The reported bug: "show only clusters" used to leave pairs shown.
    assert _env(_run("show only clusters")) == {
        "field": False,
        "isolated": False,
        "group": False,
        "cluster": True,
        "pairs": False,
    }


def test_show_only_pairs_is_distinct_from_isolated():
    assert _env(_run("show only pairs")) == {
        "field": False,
        "isolated": False,
        "group": False,
        "cluster": False,
        "pairs": True,
    }


def test_show_only_combines_named_classes():
    assert _env(_run("show only groups, clusters")) == {
        "field": False,
        "isolated": False,
        "group": True,
        "cluster": True,
        "pairs": False,
    }


def test_show_add_is_additive():
    s = _run("show groups, clusters", env_on=False)
    assert s.env_show_group and s.env_show_cluster
    assert not (s.env_show_field or s.env_show_isolated or s.env_show_pairs)


def test_hide_pairs():
    assert _run("hide pairs").env_show_pairs is False


def test_show_only_centrals_not_shadowed_by_env():
    # Greedy env regex used to swallow this and error.
    assert _run("show only centrals").filter_gal_type == "central"


def test_centrals_satellites_all_documented_forms():
    for cmd in (
        "centrals",
        "only centrals",
        "show centrals",
        "show only centrals",
    ):
        assert _run(cmd).filter_gal_type == "central"
    for cmd in (
        "satellites",
        "only satellites",
        "show satellites",
        "show only satellites",
    ):
        assert _run(cmd).filter_gal_type == "satellite"
