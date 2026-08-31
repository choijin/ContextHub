from contexthub.application.services.sensitive_data_guardrail import SensitiveDataGuardrail


def test_sensitive_data_guardrail_detects_ssn() -> None:
    result = SensitiveDataGuardrail().inspect_text("The SSN is 123-45-6789.")

    assert result.blocked is True
    assert [finding.category for finding in result.findings] == ["ssn"]


def test_sensitive_data_guardrail_detects_provider_token() -> None:
    result = SensitiveDataGuardrail().inspect_text("token = hf_abcdefghijklmnopqrstuvwxyz")

    assert result.blocked is True
    assert {finding.category for finding in result.findings} >= {
        "provider_token",
        "secret_assignment",
    }


def test_sensitive_data_guardrail_detects_phone_number() -> None:
    result = SensitiveDataGuardrail().inspect_text("Call (212) 555-0100 for assistance.")

    assert result.blocked is True
    assert [finding.category for finding in result.findings] == ["phone_number"]


def test_sensitive_data_guardrail_does_not_treat_chart_values_as_phone_number() -> None:
    result = SensitiveDataGuardrail().inspect_text(
        "Distribution of Incurred Claims\n100\n300\n1000\n3000\n2015\n2016"
    )

    assert result.blocked is False
    assert result.findings == []


def test_sensitive_data_guardrail_allows_normal_educational_text() -> None:
    result = SensitiveDataGuardrail().inspect_text(
        "Conditional probability is the probability of an event given another event."
    )

    assert result.blocked is False
    assert result.findings == []
