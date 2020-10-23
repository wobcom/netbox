from requests import post, delete
from django.conf import settings


class OdinException(Exception):
    pass


class OdinResponse:
    def __init__(self, output, has_errors):
        self.output = output
        self.has_errors = has_errors


def odin_prepare(pid):
    r = post(
        url=f"{settings.ODIN_WORKER_URL}/provision/{pid}",
        json={
            "odinArgs": settings.ODIN_ADDITIONAL_ARGS,
        },
    )

    if r.ok:
        return OdinResponse(r.text, False)
    elif r.status_code == 422:
        return OdinResponse(r.text, True)
    else:
        raise OdinException("odin_prepare: Unexpected response {}: {}".format(r.status_code, r.text))


def odin_diff(pid):
    r = post(
        url=f"{settings.ODIN_WORKER_URL}/provision/{pid}/diff",
        json=f"/ws/change/provisions/{pid}/odin/diff/",
    )

    if not r.ok:
        raise OdinException("odin_diff: Unexpected response {}: {}".format(r.status_code, r.text))


def odin_commit(pid):
    r = post(
        url=f"{settings.ODIN_WORKER_URL}/provision/{pid}/commit",
        json=f"/ws/change/provisions/{pid}/odin/commit/",
    )

    if not r.ok:
        raise OdinException("odin_commit: Unexpected response {}: {}".format(r.status_code, r.text))


def odin_rollback(pid):
    r = post(url=f"{settings.ODIN_WORKER_URL}/provision/{pid}/rollback")

    if not r.ok:
        raise OdinException("odin_rollback: Unexpected response {}: {}".format(r.status_code, r.text))


def odin_delete(pid):
    delete(
        url=f"{settings.ODIN_WORKER_URL}/provision/{pid}"
    )