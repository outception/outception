from outception.news.clusters import minhash


class TestSignatures:
    def test_same_story_different_headline_is_close(self) -> None:
        a = minhash.signature(
            "Central bank holds rates at 4.25 percent as two members vote for a cut, citing the labour market"
        )
        b = minhash.signature(
            "Central bank holds rates at 4.25 percent, two members vote for a cut over the labour market"
        )
        c = minhash.signature(
            "Holders out of the cup on penalties after a 2-2 draw in the quarter-final"
        )
        assert minhash.estimate(a, b) > minhash.estimate(a, c)
        assert minhash.estimate(a, a) == 1.0
        assert minhash.estimate(a, c) < 0.3

    def test_bands_find_near_duplicates(self) -> None:
        a = minhash.signature(
            "Council backs 12 million riverside plan after week of talks"
        )
        b = minhash.signature(
            "Council backs 12 million riverside plan after a week of talks"
        )
        assert set(minhash.band_keys(a)) & set(minhash.band_keys(b))
        assert len(minhash.band_keys(a)) == minhash.BANDS

    def test_round_trip_and_empty(self) -> None:
        sig = minhash.signature("Quick brown fox jumps over the lazy dog tonight")
        assert minhash.decode(minhash.encode(sig)) == sig
        assert len(minhash.signature("")) == minhash.NUM_PERM
        assert minhash.shingles("one two") == {"one two"}
