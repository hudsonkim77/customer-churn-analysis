"""
개선 제안 리포트를 회사 공문서 형태(제목 + 결재란)의 PDF로 만드는 모듈.
markdown -> HTML -> xhtml2pdf(PDF) 순서로 변환한다.
"""

import re
from datetime import datetime
from io import BytesIO
from pathlib import Path

import markdown as md
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from xhtml2pdf import default as pisa_default
from xhtml2pdf import pisa

FONTS_DIR = Path(__file__).parent / "fonts"
REGULAR_FONT = FONTS_DIR / "NanumGothic-Regular.ttf"
BOLD_FONT = FONTS_DIR / "NanumGothic-Bold.ttf"

_FONTS_REGISTERED = False


def _register_fonts():
    """xhtml2pdf의 @font-face(로컬 파일 경로) 로딩이 Windows에서 자꾸 실패해서,
    reportlab에 폰트를 직접 등록하고 xhtml2pdf의 기본 폰트 매핑 테이블에도
    같은 이름으로 추가해준다 — xhtml2pdf가 새 컨텍스트를 만들 때마다
    이 매핑을 복사해가므로, CreatePDF 호출 전에 한 번만 해두면 된다."""
    global _FONTS_REGISTERED
    if _FONTS_REGISTERED:
        return
    pdfmetrics.registerFont(TTFont("NanumGothic", str(REGULAR_FONT)))
    pdfmetrics.registerFont(TTFont("NanumGothic-Bold", str(BOLD_FONT)))
    pisa_default.DEFAULT_FONT["nanumgothic"] = "NanumGothic"
    pisa_default.DEFAULT_FONT["nanumgothic-bold"] = "NanumGothic-Bold"
    _FONTS_REGISTERED = True


def _approval_box_html():
    """회사 공문서 스타일 결재란(담당/팀장/부서장/대표이사 4단 결재)."""
    return """
    <table class="approval-box">
      <tr>
        <td rowspan="2" class="approval-label">결<br/>재</td>
        <td class="approval-role">담당</td>
        <td class="approval-role">팀장</td>
        <td class="approval-role">부서장</td>
        <td class="approval-role">대표이사</td>
      </tr>
      <tr>
        <td class="approval-sign">&nbsp;</td>
        <td class="approval-sign">&nbsp;</td>
        <td class="approval-sign">&nbsp;</td>
        <td class="approval-sign">&nbsp;</td>
      </tr>
    </table>
    """


def _document_header_html(title, doc_date):
    return f"""
    <table class="doc-header">
      <tr>
        <td class="doc-header-left">
          <div class="doc-label">사내보고서</div>
          <div class="doc-title">{title}</div>
          <div class="doc-meta">작성일자: {doc_date} &nbsp;|&nbsp; 작성: CS 분석팀</div>
        </td>
        <td class="doc-header-right">
          {_approval_box_html()}
        </td>
      </tr>
    </table>
    <hr class="doc-divider" />
    """


CSS = f"""
@page {{
    size: A4;
    margin: 2.2cm 1.8cm 2.2cm 1.8cm;
}}
body {{
    font-family: "NanumGothic";
    font-size: 10pt;
    line-height: 1.55;
    color: #1a1a1a;
}}
h1, h2, h3, h4 {{
    font-family: "NanumGothic-Bold";
    page-break-after: avoid;
}}
h1 {{ font-size: 16pt; margin-top: 0; }}
h2 {{ font-size: 13pt; margin-top: 16pt; border-bottom: 1px solid #999; padding-bottom: 4pt; }}
h3 {{ font-size: 11.5pt; margin-top: 12pt; }}
table {{
    border-collapse: collapse;
    width: 100%;
    margin: 8pt 0;
}}
table, th, td {{
    border: 0.6pt solid #888;
}}
th, td {{
    padding: 4pt 6pt;
    font-size: 9pt;
    vertical-align: top;
}}
tr {{
    page-break-inside: avoid;
}}
/* ── 문서 상단 결재란 ── */
.doc-header {{
    width: 100%;
    border: none;
    margin-bottom: 6pt;
}}
.doc-header td {{
    border: none;
    padding: 0;
    vertical-align: top;
}}
.doc-header-left {{
    width: 68%;
}}
.doc-label {{
    font-size: 9pt;
    color: #666;
    letter-spacing: 2pt;
}}
.doc-title {{
    font-family: "NanumGothic-Bold";
    font-size: 19pt;
    margin: 4pt 0 6pt 0;
}}
.doc-meta {{
    font-size: 9pt;
    color: #444;
}}
.doc-header-right {{
    width: 32%;
}}
.approval-box {{
    width: 100%;
    border-collapse: collapse;
    margin: 0;
    page-break-inside: avoid;
}}
.approval-box td {{
    border: 0.8pt solid #333;
    text-align: center;
    font-size: 8.5pt;
}}
.approval-label {{
    width: 16%;
    background: #f0f0f0;
    font-family: "NanumGothic-Bold";
    font-size: 9pt;
}}
.approval-role {{
    padding: 3pt 2pt;
    background: #f7f7f7;
}}
.approval-sign {{
    height: 34pt;
}}
.doc-divider {{
    border: none;
    border-top: 1.4pt solid #333;
    margin: 4pt 0 10pt 0;
}}
"""


def _break_long_tokens(text):
    """[[i-006-이용량감소-이탈신호]]나 "앱(27.3%)·이메일(37.0%)" 같은, 공백이 전혀 없는
    긴 토큰은 reportlab의 줄바꿈 로직이 끊을 지점을 못 찾아 좁은 표 셀 밖으로
    흘러넘친다(다음 칸과 겹쳐 보임). 하이픈·닫는 괄호·가운뎃점 뒤에 공백을 넣어
    그 지점에서 줄바꿈이 가능하게 한다. 표 셀(마크다운 `|` 행)에만 적용해
    본문 문장의 자연스러운 띄어쓰기는 건드리지 않는다."""

    def repl(match):
        inner = match.group(1).replace("-", "- ")
        return f"[[{inner}]]"

    text = re.sub(r"\[\[([^\]]+)\]\]", repl, text)

    def fix_table_line(line):
        stripped = line.strip()
        if not stripped.startswith("|"):
            return line
        if re.fullmatch(r"[|:\-\s]+", stripped):
            return line  # 표 구분선(|---|---|)은 markdown 파서가 그대로 인식해야 하므로 건드리지 않는다
        if "`" in line:
            return line  # 코드 스팬(`data_usage_history` 등)은 식별자를 그대로 보존해야 하므로 건드리지 않는다
        line = re.sub(r"\)(?=\S)", ") ", line)
        line = re.sub(r"·(?=\S)", "· ", line)
        line = re.sub(r"×(?=\S)", "× ", line)
        return line

    return "\n".join(fix_table_line(line) for line in text.split("\n"))


def build_report_pdf(report_body_markdown, title="고객서비스 만족도개선 리포트"):
    """리포트 마크다운(프론트매터 제거된 본문)을 공문서 형식 PDF 바이트로 변환한다."""
    _register_fonts()
    # NanumGothic에 그리스 문자(χ) 글리프가 없어 빈 칸으로 뜨므로 라틴 x로 대체한다.
    report_body_markdown = report_body_markdown.replace("χ", "x")
    report_body_markdown = _break_long_tokens(report_body_markdown)
    body_html = md.markdown(report_body_markdown, extensions=["tables", "fenced_code"])
    doc_date = datetime.now().strftime("%Y년 %m월 %d일")

    html = f"""
    <html>
    <head><style>{CSS}</style></head>
    <body>
        {_document_header_html(title, doc_date)}
        {body_html}
    </body>
    </html>
    """

    buffer = BytesIO()
    result = pisa.CreatePDF(src=html, dest=buffer, encoding="utf-8")
    if result.err:
        raise RuntimeError(f"PDF 생성 실패 (xhtml2pdf error code={result.err})")
    return buffer.getvalue()


def _load_report_body():
    report_path = Path(__file__).parent / "report" / "고객서비스_만족도개선_리포트.md"
    text = report_path.read_text(encoding="utf-8-sig")
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            text = text[end + 3 :].lstrip("\n")
    return text


if __name__ == "__main__":
    # Streamlit Cloud의 정적 파일 서빙은 배포 시점에 이미 저장소에 있던 파일만 서빙하고
    # 앱 실행 중에 쓴 파일은 반영하지 않는다(직접 검증함). 그래서 PDF를 매 클릭마다
    # 새로 만들어 static/에 쓰는 대신, 이 스크립트로 미리 만들어 저장소에 커밋해두고
    # st.link_button이 그 고정된 경로를 새 탭으로 여는 방식으로 바꿨다.
    # 리포트(report/고객서비스_만족도개선_리포트.md)가 바뀔 때마다 다시 실행하고 커밋할 것.
    out_dir = Path(__file__).parent / "static"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "고객서비스_만족도개선_리포트.pdf"
    out_path.write_bytes(build_report_pdf(_load_report_body()))
    print(f"저장 완료: {out_path} ({out_path.stat().st_size:,} bytes)")
