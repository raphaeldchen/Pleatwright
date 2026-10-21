"""Two ZeroGPU failures that need OPPOSITE responses must not share a verdict.

Observed live 2026-08-22, verbatim from the Space:

  exhaustion : "You have exceeded your free ZeroGPU quota
                (60s requested vs. 0s left). Try again in 0:00:00."
  contention : "No GPU was available after 60s. Subscribe to Pro to get the
                highest priority in ZeroGPU queues."

The first is permanent until the window resets -- retrying burns wall-clock and
cannot succeed. The second is a busy shared pool -- retrying is exactly right
and usually works within a minute.

`_is_hf_quota_error` returned True for BOTH, because it matched bare "gpu" and
treated every gradio AppError as terminal. The cost was measured: a bake-off of
12 arms drew ONE, then marked the remaining ELEVEN "UNRUN, reason quota" and
stopped -- when not one of them was out of quota. The provider also told the
operator "Retrying now is pointless" in precisely the case where retrying is
the correct move.
"""
import pytest

import mesh_acquire


EXHAUSTION = ("You have exceeded your free ZeroGPU quota (60s requested vs. "
              "0s left). Try again in 0:00:00. Subscribe to Hugging Face PRO "
              "to get 40 min of ZeroGPU quota a day")
CONTENTION = ("No GPU was available after 60s. Subscribe to Pro to get the "
              "highest priority in ZeroGPU queues.")


def _app_error(message):
    """The real channel: gradio_client raises AppError for Space-side errors."""
    from gradio_client import exceptions as gc_exc
    return gc_exc.AppError(message=message)


# ---------------------------------------------------------------------------
# the split
# ---------------------------------------------------------------------------

def test_real_exhaustion_is_terminal():
    assert mesh_acquire._is_hf_quota_error(RuntimeError(EXHAUSTION)) is True
    assert mesh_acquire._is_hf_quota_error(_app_error(EXHAUSTION)) is True


def test_gpu_contention_is_NOT_terminal():
    """THE REGRESSION THIS FILE EXISTS FOR.

    MUST-FAIL INPUT (COORDINATION.md 4.1): the shipped classifier, which
    matched bare "gpu" and blanket-trusted AppError, returns True here -- and
    that single wrong bit is what stopped a 12-arm bake-off after one draw.
    """
    assert mesh_acquire._is_hf_quota_error(RuntimeError(CONTENTION)) is False
    assert mesh_acquire._is_hf_quota_error(_app_error(CONTENTION)) is False


def test_contention_is_named_as_such():
    assert mesh_acquire._is_hf_gpu_contention_error(
        RuntimeError(CONTENTION)) is True
    assert mesh_acquire._is_hf_gpu_contention_error(
        RuntimeError(EXHAUSTION)) is False


def test_an_unrelated_app_error_is_still_terminal():
    """Carving out contention must not turn every AppError into a retry storm.

    MUST-FAIL INPUT: replacing the AppError branch with a pure string match --
    a genuine Space-side rejection would then be retried `attempts` times.
    """
    assert mesh_acquire._is_hf_quota_error(_app_error("model failed to load"))


# ---------------------------------------------------------------------------
# what the classification is FOR: retry behaviour
# ---------------------------------------------------------------------------

class _Client:
    def __init__(self, outcomes, log):
        self._outcomes, self._log = outcomes, log

    def predict(self, *args, **kwargs):
        self._log.append(args)
        out = self._outcomes[min(len(self._log) - 1, len(self._outcomes) - 1)]
        if isinstance(out, Exception):
            raise out
        return out


def _provider(outcomes, log, **kw):
    return mesh_acquire.HuggingFaceProvider(
        client_factory=lambda s, t: _Client(outcomes, log),
        sleep=lambda _s: None, **kw)


def test_contention_is_retried(tmp_path, monkeypatch):
    """A busy pool must be waited out, not surrendered to.

    MUST-FAIL INPUT: classifying contention as quota -- len(log) == 1.
    """
    glb = tmp_path / "m.glb"
    glb.write_bytes(b"glTF" + b"\x00" * 40)
    log = []
    prov = _provider([_app_error(CONTENTION), _app_error(CONTENTION),
                      str(glb)], log, attempts=3)
    out = prov.generate("an octopus", str(tmp_path / "cache"))
    assert len(log) == 3, log            # two failures, then success
    assert out.endswith("mesh.glb")


def test_exhaustion_is_not_retried(tmp_path):
    log = []
    prov = _provider([_app_error(EXHAUSTION)], log, attempts=3)
    with pytest.raises(RuntimeError, match="quota"):
        prov.generate("an octopus", str(tmp_path / "cache"))
    assert len(log) == 1, log


def test_the_two_messages_advise_differently(tmp_path):
    """"Retrying now is pointless" is actively wrong for contention.

    MUST-FAIL INPUT: one shared message -- the operator waits out a reset
    window that was never the problem.
    """
    log = []
    prov = _provider([_app_error(EXHAUSTION)], log, attempts=1)
    with pytest.raises(RuntimeError) as exhausted:
        prov.generate("x", str(tmp_path / "a"))

    log = []
    prov = _provider([_app_error(CONTENTION)], log, attempts=1)
    with pytest.raises(RuntimeError) as busy:
        prov.generate("x", str(tmp_path / "b"))

    assert "pointless" in str(exhausted.value)
    assert "pointless" not in str(busy.value)
    assert "busy" in str(busy.value).lower() or "queue" in str(busy.value).lower()


# ---------------------------------------------------------------------------
# the THIRD class: a Space that is simply broken
#
# Added 2026-08-24. VAST-AI/TripoSG answers every endpoint -- including its own
# /run_segmentation, which does no generation at all -- with a contentless
# gradio AppError. `_is_hf_quota_error` blanket-trusts AppError, so the
# provider wrapped it as "free GPU quota exhausted (...)", the bake-off row
# recorded reason=quota, and NINE further arms were never attempted. Nothing
# was out of quota; one Space was down.
#
# Note the shape of the mistake: it is not the contention bug again. Contention
# was a message that LOOKED like exhaustion. This is an exception TYPE being
# read as exhaustion with no message at all -- an inference from silence.
# ---------------------------------------------------------------------------

OPAQUE = ("The upstream Gradio app has raised an exception but has not "
          "enabled verbose error reporting")


def test_an_opaque_space_error_is_not_budget_exhaustion():
    """MUST-FAIL INPUT (COORDINATION.md 4.1): `_is_hf_quota_exhaustion_error`
    delegating to `_is_hf_quota_error`, or keeping any isinstance(AppError)
    branch of its own. That is the bug, and it costs a whole matrix."""
    assert mesh_acquire._is_hf_quota_exhaustion_error(_app_error(OPAQUE)) is False
    assert mesh_acquire._is_hf_quota_exhaustion_error(
        _app_error("model failed to load")) is False


def test_exhaustion_is_recognised_from_the_message_alone():
    """The positive half. Exhaustion must be readable WITHOUT the exception
    type, because it arrives wrapped as often as it arrives raw."""
    assert mesh_acquire._is_hf_quota_exhaustion_error(RuntimeError(EXHAUSTION))
    assert mesh_acquire._is_hf_quota_exhaustion_error(_app_error(EXHAUSTION))
    assert mesh_acquire._is_hf_quota_exhaustion_error(
        RuntimeError(CONTENTION)) is False


def test_the_two_predicates_answer_DIFFERENT_questions():
    """They are allowed to disagree, and on an opaque error they MUST.

        _is_hf_quota_error            -> retry THIS call?      -> no
        _is_hf_quota_exhaustion_error -> account out of budget? -> no

    A broken Space should not be retried (it will raise again) AND should not
    stop a twelve-arm matrix. One predicate cannot express both.

    MUST-FAIL INPUT: collapsing them back into one.
    """
    opaque = _app_error(OPAQUE)
    assert mesh_acquire._is_hf_quota_error(opaque) is True
    assert mesh_acquire._is_hf_quota_exhaustion_error(opaque) is False
