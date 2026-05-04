import secrets
import string


PRIVATE_ROOM_CODE_LENGTH = 5


def generate_private_room_code(existing_codes=None):
    existing_codes = existing_codes or set()

    alphabet = string.ascii_uppercase + string.digits

    while True:
        code = "".join(secrets.choice(alphabet) for _ in range(PRIVATE_ROOM_CODE_LENGTH))

        if code not in existing_codes:
            return code


def normalize_room_code(code):
    return str(code or "").strip().upper().replace(" ", "")


def is_valid_room_code(code):
    code = normalize_room_code(code)

    if len(code) != PRIVATE_ROOM_CODE_LENGTH:
        return False

    return code.isalnum()
