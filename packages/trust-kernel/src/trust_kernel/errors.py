class PclError(Exception):
    def __init__(self, code: str, detail: str, status: int = 400) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail
        self.status = status


class NotFound(PclError):
    def __init__(self, detail: str = "not found") -> None:
        super().__init__("not_found", detail, 404)


class ValidationFailed(PclError):
    def __init__(self, detail: str) -> None:
        super().__init__("validation_failed", detail, 422)


class VersionConflict(PclError):
    def __init__(self, detail: str = "version conflict") -> None:
        super().__init__("version_conflict", detail, 409)


class PolicyDenied(PclError):
    def __init__(self, detail: str = "policy denied") -> None:
        super().__init__("policy_denied", detail, 403)


class Revoked(PclError):
    def __init__(self, detail: str = "connection revoked") -> None:
        super().__init__("revoked", detail, 401)


class ApprovalRequired(PclError):
    def __init__(self, detail: str = "approval required") -> None:
        super().__init__("approval_required", detail, 403)


class Busy(PclError):
    def __init__(self, detail: str = "sync in progress") -> None:
        super().__init__("busy", detail, 409)


class IntegrityMismatch(PclError):
    def __init__(self, detail: str = "integrity mismatch") -> None:
        super().__init__("integrity_mismatch", detail, 400)


class ReconsentRequired(PclError):
    def __init__(self, detail: str = "reconsent required") -> None:
        super().__init__("reconsent_required", detail, 422)


class ApiVersionUnsupported(PclError):
    def __init__(self, detail: str = "api version unsupported") -> None:
        super().__init__("api_version_unsupported", detail, 422)


class ConsentRequired(PclError):
    def __init__(self, detail: str = "consent required") -> None:
        super().__init__("consent_required", detail, 422)
