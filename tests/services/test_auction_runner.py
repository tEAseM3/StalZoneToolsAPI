from app.services.auction_runner import _regions


def test_regions_parses_comma_separated_configuration():
    assert _regions("ru, EU,sea") == ["RU", "EU", "SEA"]
