from src.repositories.image_repository import build_image_pk, build_image_sk, build_tag_sk


def test_build_image_pk():
    assert build_image_pk("u1") == "USER#u1"


def test_build_image_sk():
    value = build_image_sk("2026-02-22T10:10:10Z", "img-1")
    assert value == "IMAGE#2026-02-22T10:10:10Z#img-1"


def test_build_tag_sk():
    value = build_tag_sk("sunset", "2026-02-22T10:10:10Z", "img-1")
    assert value == "TAG#sunset#TS#2026-02-22T10:10:10Z#IMG#img-1"
