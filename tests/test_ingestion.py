from io import BytesIO
from pathlib import Path
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
from app.config import Settings
from app.knowledge import Knowledge


def text_pdf():
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject({NameObject('/Type'):NameObject('/Font'), NameObject('/Subtype'):NameObject('/Type1'),
                             NameObject('/BaseFont'):NameObject('/Helvetica')})
    page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})})
    stream = DecodedStreamObject()
    stream.set_data(b'BT /F1 12 Tf 50 700 Td (Synthetic PDF policy: refunds require billing approval.) Tj ET')
    page[NameObject('/Contents')] = writer._add_object(stream)
    output = BytesIO(); writer.write(output)
    return output.getvalue()


def test_pdf_text_and_citation_metadata(tmp_path):
    kb = Knowledge(Settings(embedding_mode='offline',qdrant_path=str(tmp_path/'pdf'), qdrant_url=None))
    try:
        assert kb.ingest('policy.pdf', text_pdf()) == 1
        hits = kb.retrieve('refunds billing approval', 4)
        assert hits[0].source == 'policy.pdf'
        assert hits[0].page == 1 and hits[0].chunk == 0
        assert 'billing approval' in hits[0].text
    finally:
        kb.client.close()


def test_overlap_and_replace_shorter_document(tmp_path):
    kb = Knowledge(Settings(embedding_mode='offline',qdrant_path=str(tmp_path/'chunks'), qdrant_url=None))
    try:
        words = [f'word{i}' for i in range(500)]
        assert kb.ingest('long.txt',' '.join(words).encode()) == 3
        points,_ = kb.client.scroll(kb.collection,limit=10)
        chunks = sorted((p.payload for p in points),key=lambda p:p['chunk'])
        assert chunks[0]['text'].split()[-40:] == chunks[1]['text'].split()[:40]
        assert kb.ingest('long.txt',b'Refund billing replacement') == 1
        assert kb.count() == 1
        kb.client.close()
        kb = Knowledge(Settings(embedding_mode='offline',qdrant_path=str(tmp_path/'chunks'), qdrant_url=None))
        assert kb.count() == 1
    finally:
        kb.client.close()
