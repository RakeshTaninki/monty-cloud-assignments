from src.models.image import ListImagesQuery
from src.repositories.image_repository import ImageRepository, build_image_pk, build_image_sk, build_tag_sk


def test_build_image_pk():
    assert build_image_pk("u1") == "USER#u1"


def test_build_image_sk():
    value = build_image_sk("2026-02-22T10:10:10Z", "img-1")
    assert value == "IMAGE#2026-02-22T10:10:10Z#img-1"


def test_build_tag_sk():
    value = build_tag_sk("sunset", "2026-02-22T10:10:10Z", "img-1")
    assert value == "TAG#sunset#TS#2026-02-22T10:10:10Z#IMG#img-1"


def test_list_images_tag_filter_uses_table_get_item():
    class FakeTable:
        def query(self, **_kwargs):
            return {
                "Items": [
                    {
                        "imagePK": "USER#u1",
                        "imageSK": "IMAGE#2026-02-22T10:10:10Z#img-1",
                    }
                ],
                "LastEvaluatedKey": None,
            }

        def get_item(self, Key):
            assert Key == {"PK": "USER#u1", "SK": "IMAGE#2026-02-22T10:10:10Z#img-1"}
            return {
                "Item": {
                    "PK": "USER#u1",
                    "SK": "IMAGE#2026-02-22T10:10:10Z#img-1",
                    "visibility": "PUBLIC",
                }
            }

    repo = object.__new__(ImageRepository)
    repo._table = FakeTable()
    repo._client = None

    query = ListImagesQuery(tag="sunset", limit=10)
    result = repo.list_images("u1", query)

    assert len(result.items) == 1
    assert result.items[0]["PK"] == "USER#u1"
