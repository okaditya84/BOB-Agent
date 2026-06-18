"""Phishing-resistant step-up via WebAuthn / passkeys (py_webauthn).

This is the AAL2/AAL3 challenge the policy engine demands when risk is elevated.
The private key never leaves the user's device and credentials are origin-bound,
which is exactly why NIST 800-63B counts them as phishing-resistant.

py_webauthn is imported lazily so the core risk engine works even if the optional
WebAuthn dependency is unavailable in a given environment.
"""

from __future__ import annotations

import json
from typing import Any

from ..config import Settings
from ..store.db import Store


class WebAuthnService:
    def __init__(self, store: Store, settings: Settings) -> None:
        self.store = store
        self.settings = settings

    # ---- registration (enrol a passkey) ----
    def registration_options(self, user_id: str, ts: float) -> dict[str, Any]:
        from webauthn import generate_registration_options, options_to_json
        from webauthn.helpers import bytes_to_base64url
        from webauthn.helpers.structs import (
            AuthenticatorSelectionCriteria,
            ResidentKeyRequirement,
            UserVerificationRequirement,
        )

        options = generate_registration_options(
            rp_id=self.settings.webauthn_rp_id,
            rp_name=self.settings.webauthn_rp_name,
            user_name=user_id,
            user_id=user_id.encode("utf-8"),
            authenticator_selection=AuthenticatorSelectionCriteria(
                resident_key=ResidentKeyRequirement.PREFERRED,
                user_verification=UserVerificationRequirement.PREFERRED,
            ),
        )
        self.store.save_challenge(user_id, "register", bytes_to_base64url(options.challenge), ts)
        return json.loads(options_to_json(options))

    def verify_registration(self, user_id: str, credential: dict[str, Any]) -> dict[str, Any]:
        from webauthn import verify_registration_response
        from webauthn.helpers import base64url_to_bytes, bytes_to_base64url

        challenge_b64 = self.store.pop_challenge(user_id, "register")
        if challenge_b64 is None:
            raise ValueError("No pending registration challenge for this user.")

        verification = verify_registration_response(
            credential=json.dumps(credential),
            expected_challenge=base64url_to_bytes(challenge_b64),
            expected_rp_id=self.settings.webauthn_rp_id,
            expected_origin=self.settings.webauthn_origin,
        )
        transports = credential.get("response", {}).get("transports", [])
        self.store.save_credential(
            user_id=user_id,
            credential_id=bytes_to_base64url(verification.credential_id),
            public_key=bytes_to_base64url(verification.credential_public_key),
            sign_count=verification.sign_count,
            transports=transports,
        )
        return {"verified": True, "credential_id": bytes_to_base64url(verification.credential_id)}

    # ---- authentication (the step-up challenge) ----
    def authentication_options(self, user_id: str, ts: float) -> dict[str, Any]:
        from webauthn import generate_authentication_options, options_to_json
        from webauthn.helpers import base64url_to_bytes, bytes_to_base64url
        from webauthn.helpers.structs import (
            PublicKeyCredentialDescriptor,
            UserVerificationRequirement,
        )

        creds = self.store.get_credentials(user_id)
        if not creds:
            raise ValueError("No registered passkeys for this user; cannot step up.")

        options = generate_authentication_options(
            rp_id=self.settings.webauthn_rp_id,
            allow_credentials=[
                PublicKeyCredentialDescriptor(id=base64url_to_bytes(c["credential_id"])) for c in creds
            ],
            user_verification=UserVerificationRequirement.REQUIRED,
        )
        self.store.save_challenge(user_id, "authenticate", bytes_to_base64url(options.challenge), ts)
        return json.loads(options_to_json(options))

    def verify_authentication(self, user_id: str, credential: dict[str, Any]) -> dict[str, Any]:
        from webauthn import verify_authentication_response
        from webauthn.helpers import base64url_to_bytes

        challenge_b64 = self.store.pop_challenge(user_id, "authenticate")
        if challenge_b64 is None:
            raise ValueError("No pending step-up challenge for this user.")

        creds = self.store.get_credentials(user_id)
        match = next((c for c in creds if c["credential_id"] == credential.get("id")), None)
        if match is None:
            raise ValueError("Presented credential is not registered for this user.")

        verification = verify_authentication_response(
            credential=json.dumps(credential),
            expected_challenge=base64url_to_bytes(challenge_b64),
            expected_rp_id=self.settings.webauthn_rp_id,
            expected_origin=self.settings.webauthn_origin,
            credential_public_key=base64url_to_bytes(match["public_key"]),
            credential_current_sign_count=match["sign_count"],
            require_user_verification=True,
        )
        self.store.update_sign_count(user_id, match["credential_id"], verification.new_sign_count)
        return {"verified": True, "new_sign_count": verification.new_sign_count}
