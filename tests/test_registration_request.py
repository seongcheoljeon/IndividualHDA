"""Registration requests: version bumps and the reasons a request cannot go."""

from libs.registration_request import RegistrationRequest, bump_version, validate


def test_bump_version_is_minor_and_tolerates_garbage() -> None:
    assert bump_version("1.0") == "1.1"
    assert bump_version("2.9") == "3.0"
    assert bump_version(" 0.5 ") == "0.6"
    assert bump_version("v2") == "1.0" and bump_version("") == "1.0"


def test_validate_lists_every_problem_and_normalizes() -> None:
    ok = RegistrationRequest(" my asset ", "sop", "1.0", " note ")
    assert validate(ok) == []
    assert ok.normalized() == RegistrationRequest("my_asset", "sop", "1.0", "note")
    assert validate(RegistrationRequest("", "", "x")) == [
        "Nothing was entered.",
        "Choose a category.",
        "Version must be a number like 1.0.",
    ]
    assert validate(RegistrationRequest("1abc", "sop", "0")) == [
        "The first character cannot be a number.",
        "Version must be a number like 1.0.",
    ]
    taken = validate(
        RegistrationRequest("Water", "sop", "1.0"),
        taken=lambda name, cate: "exists" if (name, cate) == ("Water", "sop") else None,
    )
    assert taken == ["exists"]
    # An invalid name is never checked for availability.
    assert validate(
        RegistrationRequest("", "sop", "1.0"), taken=lambda *_: "exists"
    ) == ["Nothing was entered."]
