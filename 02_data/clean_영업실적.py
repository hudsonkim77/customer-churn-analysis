"""
정제_규칙_영업실적.md에 정리한 3가지 규칙을 그대로 구현한 정제 스크립트.

사용법:
    python clean_영업실적.py <입력 엑셀 경로>

규칙 (정제_규칙_영업실적.md 순서와 동일):
    1. 소속팀 forward-fill (병합 셀 채우기)
    2. 매출액·목표달성률 텍스트 -> 숫자 변환
    3. 소계 행을 개인 테이블 / 팀 요약 테이블로 분리

원본 엑셀 파일은 읽기만 하며 절대 수정하지 않는다.
"""

import argparse
import sys
from pathlib import Path

import pandas as pd


def fill_merged_team_cells(df: pd.DataFrame) -> pd.DataFrame:
    """규칙 1: 병합 셀 채우기 - 소속팀 컬럼의 결측을 위 값으로 채운다."""
    df = df.copy()
    df["소속팀"] = df["소속팀"].ffill()
    return df


def convert_text_number_columns(df: pd.DataFrame) -> pd.DataFrame:
    """규칙 2: 텍스트로 저장된 숫자 컬럼 변환.

    - 매출액: "원" 단위만 제거하고 콤마 형식은 유지한다.
    - 목표달성률: "%" 를 제거하고 100으로 나눠 소수로 통일한다.
    """
    df = df.copy()
    df["매출액"] = df["매출액"].astype(str).str.replace("원", "", regex=False).str.strip()
    rate = df["목표달성률"].astype(str).str.replace("%", "", regex=False).str.strip()
    rate = rate.replace("", pd.NA)
    df["목표달성률"] = pd.to_numeric(rate, errors="coerce") / 100
    return df


def split_subtotal_rows(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """규칙 3: 소계 행 분리.

    "담당자" 값이 "소계"로 끝나는 행을 개인 테이블에서 제외하고,
    별도의 팀 요약 테이블로 분리한다. 팀 개수·담당자 수에 의존하지 않는다.
    """
    is_subtotal = df["담당자"].astype(str).str.endswith("소계")

    individual = df[~is_subtotal].reset_index(drop=True)

    summary = df[is_subtotal].reset_index(drop=True).rename(columns={"담당자": "구분"})
    if "목표달성률" in summary.columns:
        summary = summary.drop(columns=["목표달성률"])

    return individual, summary


def revenue_to_number(series: pd.Series) -> pd.Series:
    """콤마 형식 매출액 문자열("76,380,000")을 합계 계산용 숫자로 변환."""
    return pd.to_numeric(series.astype(str).str.replace(",", "", regex=False), errors="coerce")


def clean(input_path: Path) -> tuple[pd.DataFrame, pd.DataFrame, int]:
    raw = pd.read_excel(input_path, sheet_name=0)
    before_rows = len(raw)

    df = fill_merged_team_cells(raw)
    df = convert_text_number_columns(df)
    individual, summary = split_subtotal_rows(df)

    return individual, summary, before_rows


def main() -> None:
    parser = argparse.ArgumentParser(description="영업실적 messy 엑셀 정제 스크립트")
    parser.add_argument("input_path", type=Path, help="정제할 입력 엑셀(.xlsx) 파일 경로")
    args = parser.parse_args()

    input_path: Path = args.input_path
    if not input_path.exists():
        sys.exit(f"입력 파일을 찾을 수 없습니다: {input_path}")

    individual, summary, before_rows = clean(input_path)

    stem = input_path.stem
    out_dir = input_path.parent
    individual_path = out_dir / f"{stem}_clean.csv"
    summary_path = out_dir / f"{stem}_팀요약.csv"

    # 원본 파일을 절대 덮어쓰지 않도록 출력 경로가 입력 경로와 겹치지 않는지 확인
    for out_path in (individual_path, summary_path):
        if out_path.resolve() == input_path.resolve():
            sys.exit(f"출력 경로가 입력 파일과 같습니다. 중단합니다: {out_path}")

    individual.to_csv(individual_path, index=False, encoding="utf-8-sig")
    summary.to_csv(summary_path, index=False, encoding="utf-8-sig")

    total_revenue = revenue_to_number(individual["매출액"]).sum()

    print("=== 정제 결과 ===")
    print(f"정제 전 행 수(원본): {before_rows}")
    print(f"정제 후 개인 테이블 행 수: {len(individual)}")
    print(f"정제 후 팀 요약 테이블 행 수: {len(summary)}")
    print(f"정제 후 매출액 합계(개인 테이블 기준): {total_revenue:,.0f}")
    print()
    print(f"저장: {individual_path}")
    print(f"저장: {summary_path}")


if __name__ == "__main__":
    main()
