import pytest

from app.core.errors import AppError
from app.services import document_extractor as ex
from tests.helpers import make_docx


def test_docx_extracts_text_with_paragraph_refs():
    r = ex.extract("g.docx", make_docx())
    assert "TechNova" in r["text"] and r["units"][0]["ref"] == {"paragraph": 1}


def test_rejects_unsupported_type():
    with pytest.raises(AppError) as e:
        ex.extract("a.txt", b"hello")
    assert e.value.code == "UNSUPPORTED_FILE_TYPE"


def test_rejects_wrong_signature():
    with pytest.raises(AppError) as e:
        ex.extract("fake.docx", b"not a zip")
    assert e.value.code == "UNSUPPORTED_FILE_TYPE"


def test_rejects_empty_docx():
    with pytest.raises(AppError) as e:
        ex.extract("e.docx", make_docx(["hi"]))
    assert e.value.code == "EMPTY_DOCUMENT"


def test_rejects_too_large(monkeypatch):
    monkeypatch.setenv("MAX_UPLOAD_MB", "0")
    with pytest.raises(AppError) as e:
        ex.extract("g.docx", make_docx())
    assert e.value.code == "FILE_TOO_LARGE"
