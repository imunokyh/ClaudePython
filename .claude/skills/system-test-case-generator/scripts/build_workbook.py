"""Validate a test-case JSON and build the test specification workbook (.xlsx).

Usage:
    python build_workbook.py TC_JSON --out RESULT.xlsx [--force]

Checks (errors block workbook creation unless --force):
  - unique IDs, required fields filled, valid sheet/origin/technique values
  - backward traceability: every TC references existing test basis IDs
  - forward traceability / coverage: every test basis item is covered by >= 1 TC
  - equivalence partitioning and boundary value analysis applied per basis item,
    or a reason given in technique_notes
  - at least one "WoW 검증" edge case exists
  - pairwise TCs reference an existing PICT model row, and every PICT row is used
Warnings (printed, do not block): vague wording, suspected duplicate TCs.

See references/json_schema.md for the input format.
"""
import argparse
import json
import sys
from collections import defaultdict

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

SHEETS = {"기능": "기능 테스트", "비기능": "비기능 테스트"}
ORIGINS = {"기본", "제안"}
TECHNIQUES = {
    "동치 클래스", "경계값 분석", "페어와이즈(PICT)", "WoW 검증", "요구사항 기반 테스트",
    "결함 주입", "오류 추측", "상태 전이", "결정 테이블",
}
EP, BVA, PW, WOW = "동치 클래스", "경계값 분석", "페어와이즈(PICT)", "WoW 검증"
VAGUE = ["정상 동작", "정상적으로", "올바르게", "적절히", "적절한", "유효한 값", "임의의 값", "잘 동작", "문제 없"]

# (field key, default header, column width)
DEFAULT_COLUMNS = [
    ("tc_id", "테스트 케이스 ID", 14),
    ("origin", "구분", 7),
    ("basis_ids", "테스트 베이시스 ID", 16),
    ("objective", "테스트 목적", 36),
    ("preconditions", "사전 조건", 32),
    ("inputs", "입력값", 30),
    ("procedure", "절차", 44),
    ("expected", "예상 출력값", 40),
    ("techniques", "사용한 테스트 기법", 20),
    ("pict_ref", "PICT 참조", 12),
    ("remarks", "비고", 24),
]
REQUIRED_FIELDS = ["tc_id", "basis_ids", "objective", "preconditions", "inputs", "procedure", "expected", "techniques", "origin"]

HEADER_FILL = PatternFill("solid", fgColor="1F4E78")
HEADER_FONT = Font(bold=True, color="FFFFFF")
PROPOSAL_FILL = PatternFill("solid", fgColor="FFF2CC")
FAIL_FILL = PatternFill("solid", fgColor="F8CBAD")
THIN = Side(style="thin", color="A6A6A6")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
WRAP = Alignment(wrap_text=True, vertical="top")


def as_list(v):
    if v is None or v == "":
        return []
    return v if isinstance(v, list) else [v]


def fmt(key, v):
    if key == "procedure":
        steps = as_list(v)
        return "\n".join(f"{i}. {s}" for i, s in enumerate(steps, 1))
    if isinstance(v, list):
        return ", ".join(str(x) for x in v)
    return "" if v is None else str(v)


def validate(data):
    errors, warnings = [], []
    basis = data.get("test_basis") or []
    tcs = data.get("test_cases") or []
    models = {m.get("id"): m for m in data.get("pict_models") or []}
    if not basis:
        errors.append("test_basis가 비어 있습니다.")
    if not tcs:
        errors.append("test_cases가 비어 있습니다.")

    basis_ids = {}
    for b in basis:
        bid = b.get("id")
        if not bid:
            errors.append(f"ID 없는 베이시스 항목: {b}")
            continue
        if bid in basis_ids:
            errors.append(f"베이시스 ID 중복: {bid}")
        basis_ids[bid] = b
        if b.get("type") not in SHEETS:
            errors.append(f"{bid}: type은 '기능' 또는 '비기능'이어야 합니다 (현재: {b.get('type')!r}).")

    seen, used_rows, signatures = set(), defaultdict(set), {}
    for tc in tcs:
        tid = tc.get("tc_id") or "<ID 없음>"
        if tid in seen:
            errors.append(f"TC ID 중복: {tid}")
        seen.add(tid)
        for f in REQUIRED_FIELDS:
            if not as_list(tc.get(f)) or all(str(x).strip() == "" for x in as_list(tc.get(f))):
                errors.append(f"{tid}: 필수 항목 '{f}' 비어 있음")
        if tc.get("sheet") not in SHEETS:
            errors.append(f"{tid}: sheet는 '기능' 또는 '비기능'이어야 합니다.")
        if tc.get("origin") and tc["origin"] not in ORIGINS:
            errors.append(f"{tid}: origin은 '기본' 또는 '제안'이어야 합니다.")
        for bid in as_list(tc.get("basis_ids")):
            if bid not in basis_ids:
                errors.append(f"{tid}: 존재하지 않는 베이시스 ID '{bid}' (역방향 추적성 위반)")
        techs = as_list(tc.get("techniques"))
        for t in techs:
            if t not in TECHNIQUES:
                errors.append(f"{tid}: 허용되지 않은 기법 '{t}'. 허용: {sorted(TECHNIQUES)}")
        if PW in techs:
            ref = tc.get("pict_ref") or ""
            mid, _, row = ref.partition("#")
            if mid not in models:
                errors.append(f"{tid}: 페어와이즈 케이스의 pict_ref '{ref}'가 pict_models에 없습니다.")
            elif not row.isdigit() or not 1 <= int(row) <= len(models[mid].get("rows", [])):
                errors.append(f"{tid}: pict_ref 행 번호 '{ref}'가 범위를 벗어났습니다.")
            else:
                used_rows[mid].add(int(row))
        for f in ("inputs", "expected"):
            text = fmt(f, tc.get(f))
            for w in VAGUE:
                if w in text:
                    warnings.append(f"{tid}: '{f}'에 모호한 표현 '{w}' - 구체적인 값/신호로 바꾸세요.")
        sig = (fmt("preconditions", tc.get("preconditions")), fmt("inputs", tc.get("inputs")),
               fmt("procedure", tc.get("procedure")), fmt("expected", tc.get("expected")))
        if sig in signatures:
            warnings.append(f"{tid}: {signatures[sig]}와 사전 조건/입력/절차/예상 결과가 동일 - 중복 의심")
        else:
            signatures[sig] = tid

    for mid, m in models.items():
        missing = sorted(set(range(1, len(m.get("rows", [])) + 1)) - used_rows[mid])
        if missing:
            errors.append(f"{mid}: PICT 결과 행 {missing}에 대응하는 TC가 없습니다.")

    if tcs and not any(WOW in as_list(tc.get("techniques")) for tc in tcs):
        errors.append("'WoW 검증' 기법의 엣지 케이스가 하나도 없습니다.")

    by_basis = defaultdict(list)
    for tc in tcs:
        for bid in as_list(tc.get("basis_ids")):
            by_basis[bid].append(tc)
    for bid, b in basis_ids.items():
        linked = by_basis.get(bid, [])
        if not linked:
            errors.append(f"{bid}: 커버하는 TC가 없습니다 (정방향 추적성/커버리지 위반).")
            continue
        techs = {t for tc in linked for t in as_list(tc.get("techniques"))}
        note = (b.get("technique_notes") or "").strip()
        for t in (EP, BVA):
            if t not in techs and not note:
                errors.append(f"{bid}: '{t}' 미적용. 적용하거나 technique_notes에 미적용 사유를 적으세요.")
        if all(tc.get("origin") == "제안" for tc in linked):
            warnings.append(f"{bid}: '제안' 케이스로만 커버됩니다. 요구사항이 검증 불가하면 issues에 질의를 남기세요.")
    return errors, warnings, by_basis


def style_header(ws, row, ncols):
    for c in range(1, ncols + 1):
        cell = ws.cell(row=row, column=c)
        cell.fill, cell.font, cell.border = HEADER_FILL, HEADER_FONT, BORDER
        cell.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")


def write_table(ws, headers, rows, widths=None, start_row=1, highlight=None):
    for c, h in enumerate(headers, 1):
        ws.cell(row=start_row, column=c, value=h)
    style_header(ws, start_row, len(headers))
    for r, values in enumerate(rows, start_row + 1):
        fill = highlight(values) if highlight else None
        for c, v in enumerate(values, 1):
            cell = ws.cell(row=r, column=c, value=v)
            cell.alignment, cell.border = WRAP, BORDER
            if fill:
                cell.fill = fill
    if widths:
        for c, w in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(c)].width = w
    return start_row + len(rows)


def tc_sheets_default(wb, tcs):
    headers = [h for _, h, _ in DEFAULT_COLUMNS]
    widths = [w for _, _, w in DEFAULT_COLUMNS]
    first = True
    for key, title in SHEETS.items():
        ws = wb.active if first else wb.create_sheet()
        first = False
        ws.title = title
        rows = [[fmt(k, tc.get(k)) for k, _, _ in DEFAULT_COLUMNS] for tc in tcs if tc.get("sheet") == key]
        write_table(ws, headers, rows, widths, highlight=lambda v: PROPOSAL_FILL if v[1] == "제안" else None)
        ws.freeze_panes = "B2"
        ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{max(1, len(rows) + 1)}"


def tc_sheets_template(tpl, tcs, warnings):
    wb = load_workbook(tpl["path"])
    header_row = int(tpl.get("header_row", 1))
    colmap = {str(k).strip(): v for k, v in (tpl.get("column_map") or {}).items()}
    sheet_names = tpl.get("sheets") or {}
    base_name = sheet_names.get("기능") or wb.sheetnames[0]
    # Resolve (and copy) every target sheet before filling any of them, so copies start from the pristine template.
    targets = {}
    for key in SHEETS:
        name = sheet_names.get(key) or (base_name if key == "기능" else None)
        if name:
            targets[key] = wb[name]
        else:
            ws = wb.copy_worksheet(wb[base_name])
            ws.title = SHEETS[key]
            targets[key] = ws
            warnings.append(f"양식에 '{key}' 시트가 지정되지 않아 '{base_name}' 시트를 복사해 '{ws.title}'로 만들었습니다.")
    for key, ws in targets.items():
        cols = {}
        for c in range(1, ws.max_column + 1):
            h = ws.cell(row=header_row, column=c).value
            if h is not None and str(h).strip() in colmap:
                cols[colmap[str(h).strip()]] = c
        next_col = ws.max_column + 1
        for f in REQUIRED_FIELDS + (["pict_ref"] if any(tc.get("pict_ref") for tc in tcs) else []):
            if f not in cols:
                header = dict((k, h) for k, h, _ in DEFAULT_COLUMNS)[f]
                hc = ws.cell(row=header_row, column=next_col, value=header)
                hc.fill, hc.font, hc.border = HEADER_FILL, HEADER_FONT, BORDER
                cols[f] = next_col
                warnings.append(f"양식 '{ws.title}'에 '{header}' 열이 없어 {get_column_letter(next_col)}열에 추가했습니다.")
                next_col += 1
        r = header_row + 1
        for tc in (t for t in tcs if t.get("sheet") == key):
            for f, c in cols.items():
                cell = ws.cell(row=r, column=c, value=fmt(f, tc.get(f)))
                cell.alignment, cell.border = WRAP, BORDER
                if tc.get("origin") == "제안":
                    cell.fill = PROPOSAL_FILL
            r += 1
    return wb


def add_trace_sheet(wb, data, by_basis):
    ws = wb.create_sheet("추적성 매트릭스")
    headers = ["테스트 베이시스 ID", "제목", "유형", "ASIL", "요구사항", "TC (기본)", "TC (제안)",
               "적용 기법", "기법 미적용 사유", "커버 여부"]
    rows = []
    for b in data["test_basis"]:
        linked = by_basis.get(b["id"], [])
        techs = sorted({t for tc in linked for t in as_list(tc.get("techniques"))})
        rows.append([
            b["id"], b.get("title", ""), b.get("type", ""), b.get("asil", ""), b.get("text", ""),
            ", ".join(tc["tc_id"] for tc in linked if tc.get("origin") != "제안"),
            ", ".join(tc["tc_id"] for tc in linked if tc.get("origin") == "제안"),
            ", ".join(techs), b.get("technique_notes", ""), "O" if linked else "X",
        ])
    write_table(ws, headers, rows, [16, 22, 8, 7, 48, 26, 18, 30, 26, 9],
                highlight=lambda v: FAIL_FILL if v[-1] == "X" else None)
    ws.freeze_panes = "B2"


def add_summary_sheet(wb, data, by_basis):
    ws = wb.create_sheet("커버리지 요약")
    basis, tcs = data["test_basis"], data["test_cases"]
    covered = sum(1 for b in basis if by_basis.get(b["id"]))
    traced = sum(1 for tc in tcs if as_list(tc.get("basis_ids")))
    tech_count = defaultdict(int)
    for tc in tcs:
        for t in as_list(tc.get("techniques")):
            tech_count[t] += 1
    rows = [
        ["프로젝트", data.get("project", "")],
        ["테스트 레벨", data.get("test_level", "")],
        ["테스트 베이시스 출처", data.get("test_basis_source", "")],
        ["테스트 베이시스 항목 수", len(basis)],
        ["  - 기능 / 비기능", f"{sum(b.get('type') == '기능' for b in basis)} / {sum(b.get('type') == '비기능' for b in basis)}"],
        ["커버된 베이시스 항목 수", covered],
        ["테스트 베이시스 커버리지", f"{covered / len(basis) * 100:.1f}%" if basis else "-"],
        ["TC → 베이시스 추적성", f"{traced / len(tcs) * 100:.1f}%" if tcs else "-"],
        ["테스트 케이스 수", len(tcs)],
        ["  - 기능 / 비기능", f"{sum(tc.get('sheet') == '기능' for tc in tcs)} / {sum(tc.get('sheet') == '비기능' for tc in tcs)}"],
        ["  - 기본 / 제안", f"{sum(tc.get('origin') == '기본' for tc in tcs)} / {sum(tc.get('origin') == '제안' for tc in tcs)}"],
        ["질의 사항 수", len(data.get("issues") or [])],
    ]
    end = write_table(ws, ["항목", "값"], rows, [28, 40])
    write_table(ws, ["기법", "TC 수"], sorted(tech_count.items(), key=lambda x: -x[1]), start_row=end + 2)


def add_pict_sheet(wb, data):
    models = data.get("pict_models") or []
    if not models:
        return
    ws = wb.create_sheet("PICT 모델")
    tc_by_ref = defaultdict(list)
    for tc in data["test_cases"]:
        if tc.get("pict_ref"):
            tc_by_ref[tc["pict_ref"]].append(tc["tc_id"])
    r = 1
    for m in models:
        ws.cell(row=r, column=1, value=f"{m['id']}  ({m.get('order', 2)}-way)").font = Font(bold=True, size=12)
        ws.cell(row=r + 1, column=1, value="명령")
        ws.cell(row=r + 1, column=2, value=m.get("command", ""))
        ws.cell(row=r + 2, column=1, value="모델")
        c = ws.cell(row=r + 2, column=2, value=m.get("model", ""))
        c.alignment = WRAP
        ws.row_dimensions[r + 2].height = 15 * (m.get("model", "").count("\n") + 1)
        header = ["#"] + m.get("header", []) + ["TC ID"]
        rows = [[i] + [row.get(h, "") for h in m.get("header", [])] + [", ".join(tc_by_ref.get(f"{m['id']}#{i}", []))]
                for i, row in enumerate(m.get("rows", []), 1)]
        r = write_table(ws, header, rows, start_row=r + 4) + 3
    ws.column_dimensions["A"].width = 10
    ws.column_dimensions["B"].width = 50


def add_issue_sheet(wb, data):
    issues = data.get("issues") or []
    if not issues:
        return
    ws = wb.create_sheet("질의 사항")
    rows = [[i.get("id", ""), i.get("basis_id", ""), i.get("question", ""), i.get("impact", "")] for i in issues]
    write_table(ws, ["ID", "베이시스 ID", "질의 내용", "영향/가정"], rows, [8, 16, 60, 50])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tc_json")
    ap.add_argument("--out", required=True)
    ap.add_argument("--force", action="store_true", help="Build the workbook even if validation fails")
    args = ap.parse_args()

    with open(args.tc_json, encoding="utf-8") as f:
        data = json.load(f)

    errors, warnings, by_basis = validate(data)
    for w in warnings:
        print("WARNING:", w)
    for e in errors:
        print("ERROR:", e)
    if errors and not args.force:
        sys.exit(f"\n검증 실패: 오류 {len(errors)}건. 엑셀을 만들지 않았습니다.")

    tpl = data.get("template")
    if tpl:
        template_warnings = []
        wb = tc_sheets_template(tpl, data["test_cases"], template_warnings)
        for w in template_warnings:
            print("WARNING:", w)
        warnings += template_warnings
    else:
        wb = Workbook()
        tc_sheets_default(wb, data["test_cases"])
    add_trace_sheet(wb, data, by_basis)
    add_summary_sheet(wb, data, by_basis)
    add_pict_sheet(wb, data)
    add_issue_sheet(wb, data)
    wb.save(args.out)

    basis = data["test_basis"]
    covered = sum(1 for b in basis if by_basis.get(b["id"]))
    print(f"\nOK: {args.out}")
    print(f"  베이시스 커버리지 {covered}/{len(basis)} ({covered / len(basis) * 100:.1f}%), "
          f"TC {len(data['test_cases'])}건, 오류 {len(errors)}, 경고 {len(warnings)}")


if __name__ == "__main__":
    main()
