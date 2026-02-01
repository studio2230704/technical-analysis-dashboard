"""AI-powered stock analysis using Claude API."""

import os
from dataclasses import dataclass
from typing import Optional

from anthropic import Anthropic
from dotenv import load_dotenv


load_dotenv()


@dataclass
class AnalysisResult:
    """Result of AI analysis."""

    analysis_type: str
    content: str
    ticker: str
    success: bool
    error: Optional[str] = None


# Analysis prompts based on skills
FUNDAMENTAL_ANALYSIS_PROMPT = """あなたは機関投資家のリサーチアナリストです。
以下のティッカーシンボルの企業について、ファンダメンタル分析を行ってください。

ティッカー: {ticker}
企業名: {company_name}

## 分析項目

1. **売上高・営業利益・純利益の推移**（過去5年の傾向）
2. **利益率の変化**（粗利率、営業利益率、純利益率）
3. **キャッシュフロー分析**（営業CF、投資CF、フリーCF）
4. **バランスシート健全性**（自己資本比率、流動比率、D/Eレシオ）
5. **バリュエーション指標**（PER、PBR、EV/EBITDA）

## 出力ルール

- 数値には出典を明記（SEC EDGAR、Yahoo Finance等）
- 前年同期比（YoY）を併記
- 業界平均との比較を含める
- 「事実」「ガイダンス」「推測」を明確に区分

## 提供データ

{financial_data}

上記のデータを基に、包括的なファンダメンタル分析レポートを作成してください。
日本語で回答してください。"""


MACRO_ANALYSIS_PROMPT = """あなたはマクロ経済の専門アナリストです。
以下のティッカーシンボルの企業に関連するマクロ環境分析を行ってください。

ティッカー: {ticker}
企業名: {company_name}
セクター: {sector}

## 分析項目

1. **金利環境**（FRBの政策金利、イールドカーブの状況）
2. **為替動向**（主要通貨の動向と企業への影響）
3. **業界トレンド**（TAM推移、競合動向）
4. **規制環境**（セクター固有の規制リスク）
5. **地政学リスク**（サプライチェーンへの影響）

## 出力ルール

- 「確認済み事実」と「市場の見方」を区別
- 直近6ヶ月の変化に焦点
- 企業への具体的な影響を記述

日本語で回答してください。"""


RISK_ASSESSMENT_PROMPT = """あなたはリスク管理の専門家です。
以下のティッカーシンボルの企業について、リスク評価を行ってください。

ティッカー: {ticker}
企業名: {company_name}

## 評価項目（各項目を5段階で評価: 1=低リスク → 5=高リスク）

1. **バリュエーションリスク**（割高度合い）
2. **業績リスク**（ガイダンス未達のリスク）
3. **マクロリスク**（金利・為替・景気への感応度）
4. **競合リスク**（市場シェア喪失のリスク）
5. **規制リスク**（規制強化の影響）

## 出力形式

各リスク項目について:
- リスクスコア（1-5）
- 根拠の説明
- リスク緩和要因（あれば）

最後に:
- **総合リスクスコア**（平均）
- **最悪シナリオの想定ダウンサイド**（%）

## 提供データ

{financial_data}

日本語で回答してください。"""


INVESTMENT_SUMMARY_PROMPT = """あなたは投資アドバイザーです。
以下の分析結果を統合し、投資判断のための総合サマリーを作成してください。

ティッカー: {ticker}
企業名: {company_name}

## ファンダメンタル分析結果
{fundamental_analysis}

## マクロ分析結果
{macro_analysis}

## リスク評価結果
{risk_assessment}

## 出力形式

### エグゼクティブサマリー
- 2-3文で企業の投資魅力度を要約

### 強み（Strengths）
- 箇条書きで3-5点

### 弱み（Weaknesses）
- 箇条書きで3-5点

### 機会（Opportunities）
- 箇条書きで2-3点

### 脅威（Threats）
- 箇条書きで2-3点

### 注目ポイント
- 今後3-6ヶ月で注目すべきイベント・指標

⚠️ **免責事項**: この分析は情報提供のみを目的としており、投資助言ではありません。
投資判断は自己責任で行ってください。

日本語で回答してください。"""


def get_client() -> Optional[Anthropic]:
    """Get Anthropic client if API key is available."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    return Anthropic(api_key=api_key)


def run_analysis(
    prompt: str,
    analysis_type: str,
    ticker: str,
    max_tokens: int = 4096,
) -> AnalysisResult:
    """Run AI analysis using Claude API.

    Args:
        prompt: The analysis prompt
        analysis_type: Type of analysis (fundamental, macro, risk, summary)
        ticker: Stock ticker symbol
        max_tokens: Maximum tokens in response

    Returns:
        AnalysisResult with analysis content or error
    """
    client = get_client()

    if client is None:
        return AnalysisResult(
            analysis_type=analysis_type,
            content="",
            ticker=ticker,
            success=False,
            error="ANTHROPIC_API_KEY が設定されていません。.env ファイルまたは Streamlit Secrets に設定してください。",
        )

    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=max_tokens,
            messages=[
                {"role": "user", "content": prompt}
            ],
        )

        content = message.content[0].text

        return AnalysisResult(
            analysis_type=analysis_type,
            content=content,
            ticker=ticker,
            success=True,
        )

    except Exception as e:
        return AnalysisResult(
            analysis_type=analysis_type,
            content="",
            ticker=ticker,
            success=False,
            error=str(e),
        )


def analyze_fundamental(
    ticker: str,
    company_name: str,
    financial_data: str,
) -> AnalysisResult:
    """Run fundamental analysis."""
    prompt = FUNDAMENTAL_ANALYSIS_PROMPT.format(
        ticker=ticker,
        company_name=company_name,
        financial_data=financial_data,
    )
    return run_analysis(prompt, "fundamental", ticker)


def analyze_macro(
    ticker: str,
    company_name: str,
    sector: str = "Technology",
) -> AnalysisResult:
    """Run macro environment analysis."""
    prompt = MACRO_ANALYSIS_PROMPT.format(
        ticker=ticker,
        company_name=company_name,
        sector=sector,
    )
    return run_analysis(prompt, "macro", ticker)


def analyze_risk(
    ticker: str,
    company_name: str,
    financial_data: str,
) -> AnalysisResult:
    """Run risk assessment."""
    prompt = RISK_ASSESSMENT_PROMPT.format(
        ticker=ticker,
        company_name=company_name,
        financial_data=financial_data,
    )
    return run_analysis(prompt, "risk", ticker)


def generate_investment_summary(
    ticker: str,
    company_name: str,
    fundamental_analysis: str,
    macro_analysis: str,
    risk_assessment: str,
) -> AnalysisResult:
    """Generate comprehensive investment summary."""
    prompt = INVESTMENT_SUMMARY_PROMPT.format(
        ticker=ticker,
        company_name=company_name,
        fundamental_analysis=fundamental_analysis,
        macro_analysis=macro_analysis,
        risk_assessment=risk_assessment,
    )
    return run_analysis(prompt, "summary", ticker, max_tokens=2048)


def is_api_key_configured() -> bool:
    """Check if Anthropic API key is configured."""
    return bool(os.getenv("ANTHROPIC_API_KEY"))
