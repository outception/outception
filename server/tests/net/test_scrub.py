from outception.net.scrub import SCRUB_VERSION, luhn_ok, scrub, scrub_report


class TestClasses:
    def test_email(self) -> None:
        assert (
            scrub("Write to jane.doe+news@example.co.uk today")
            == "Write to [email] today"
        )

    def test_phone_needs_separators_or_a_country_code(self) -> None:
        assert scrub("Call +353 1 234 5678 now") == "Call [phone] now"
        assert scrub("Call (415) 555-0199 now") == "Call [phone] now"
        # A bare run of digits is a figure, not a number to redact.
        assert (
            scrub("The budget was 1234567890 last year")
            == "The budget was 1234567890 last year"
        )

    def test_secrets(self) -> None:
        assert scrub("key sk-abcdefghijklmnopqrstuvwxyz1234") == "key [secret]"
        assert (
            scrub("token ghp_abcdefghijklmnopqrstuvwxyz0123456789") == "token [secret]"
        )
        assert scrub("AKIAABCDEFGHIJKLMNOP leaked") == "[secret] leaked"
        assert scrub("db postgres://user:pw@host:5432/db") == "db [secret]"
        jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
        assert scrub(f"bearer {jwt}") == "bearer [secret]"
        block = "-----BEGIN PRIVATE KEY-----\nMIIE\n-----END PRIVATE KEY-----"
        assert scrub(f"see {block} end") == "see [secret] end"

    def test_card_needs_the_checksum(self) -> None:
        assert luhn_ok("4111111111111111")
        assert scrub("paid with 4111 1111 1111 1111") == "paid with [card]"
        assert (
            scrub("order 4111 1111 1111 1112 shipped")
            == "order 4111 1111 1111 1112 shipped"
        )

    def test_national_ids(self) -> None:
        assert scrub("PPS 1234567TW please") == "PPS [id] please"
        assert (
            scrub("PPS 1234567FB please") == "PPS 1234567FB please"
        )  # wrong check letter
        assert scrub("NI number AB 12 34 56 C") == "NI number [id]"
        assert scrub("SSN 123-45-6789") == "SSN [id]"

    def test_ip_only_near_a_keyword(self) -> None:
        assert (
            scrub("the server at 10.1.2.3 answered")
            == "the server at [address] answered"
        )
        assert (
            scrub("the match ended 10.1.2.3 on aggregate")
            == "the match ended 10.1.2.3 on aggregate"
        )


class TestReport:
    def test_counts_and_version(self) -> None:
        report = scrub_report("mail a@b.io or b@c.io, call +1 212 555 0100")
        assert report.changed
        assert report.hits == {"email": 2, "phone": 1}
        assert SCRUB_VERSION == 1

    def test_plain_copy_is_untouched_and_cheap(self) -> None:
        copy = "The council backed the plan after a week of talks, critics object."
        report = scrub_report(copy)
        assert report.text == copy
        assert not report.changed
