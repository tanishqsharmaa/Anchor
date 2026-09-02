"""
html_renderer.py — HTML5 Preview Renderer for AutoDeck AI React Slide Studio
"""

import html
from typing import List

from anchor.deck.schemas import (
    SlideType,
    SlideDeckAST,
    SlideItem,
    HeroSlideContent,
    BLUFSlideContent,
    PolicyMatrixSlideContent,
    FinancialDelegationSlideContent,
)


class HTMLRenderer:
    """
    Renders SlideDeckAST and SlideItem objects into responsive, semantic HTML5/CSS payloads
    compatible with the Next.js 15 C4ISR Dark Tactical theme in Slide Studio.
    """

    def render_deck(self, deck_ast: SlideDeckAST) -> List[str]:
        """
        Compile entire SlideDeckAST into a list of HTML5 slide strings.

        Args:
            deck_ast: Validated SlideDeckAST.

        Returns:
            List[str]: Array of HTML5 slide markup strings.
        """
        total = len(deck_ast.slides)
        return [
            self.render_slide(slide_item, idx + 1, total, deck_ast.dtg)
            for idx, slide_item in enumerate(deck_ast.slides)
        ]

    def render_slide(
        self,
        item: SlideItem,
        slide_num: int = 1,
        total_slides: int = 1,
        dtg: str = "",
    ) -> str:
        """
        Render a single SlideItem into an HTML5 slide component.
        """
        classification = html.escape(item.classification or "RESTRICTED // FOR OFFICIAL USE ONLY")

        if item.type == SlideType.HERO_SLIDE:
            body_html = self._render_hero_html(item)
        elif item.type == SlideType.BLUF_EXECUTIVE:
            body_html = self._render_bluf_html(item)
        elif item.type == SlideType.POLICY_MATRIX:
            body_html = self._render_policy_matrix_html(item)
        elif item.type == SlideType.FINANCIAL_DELEGATION:
            body_html = self._render_financial_delegation_html(item)
        else:
            body_html = f"<div class='p-6 text-slate-300'>{html.escape(str(item.content))}</div>"

        footer_dtg = html.escape(dtg) if dtg else ""

        return (
            f"<section class='c4isr-slide relative w-full aspect-[16/9] bg-[#0A192F] text-slate-100 rounded-lg p-6 flex flex-col justify-between border border-[#233554] shadow-2xl overflow-hidden font-sans' data-slide-id='{html.escape(item.slide_id)}'>\n"
            f"  <!-- Top Classification Banner -->\n"
            f"  <header class='text-center text-[10px] tracking-widest font-bold text-red-500 uppercase border-b border-[#233554]/50 pb-1'>\n"
            f"    {classification}\n"
            f"  </header>\n\n"
            f"  <!-- Slide Body Content -->\n"
            f"  <div class='my-auto w-full'>\n"
            f"    {body_html}\n"
            f"  </div>\n\n"
            f"  <!-- Footer & Telemetry -->\n"
            f"  <footer class='flex justify-between items-center text-[10px] font-mono text-slate-400 border-t border-[#233554]/50 pt-2'>\n"
            f"    <span>{footer_dtg}</span>\n"
            f"    <span>PROJECT ANCHOR // PAGE {slide_num:02d} OF {total_slides:02d}</span>\n"
            f"    <span class='text-red-500 font-bold uppercase'>{classification}</span>\n"
            f"  </footer>\n"
            f"</section>"
        )

    def _render_hero_html(self, item: SlideItem) -> str:
        content: HeroSlideContent = (
            item.content if isinstance(item.content, HeroSlideContent)
            else HeroSlideContent.model_validate(item.content)
        )
        title = html.escape(content.title)
        subtitle = f"<h2 class='text-xl text-[#FFD700] font-medium mt-2'>{html.escape(content.subtitle)}</h2>" if content.subtitle else ""
        officer = html.escape(content.officer or "STAFF OFFICER (OPERATIONS)")
        unit = html.escape(content.unit or "INTEGRATED HQ MOD (NAVY)")

        return (
            f"    <div class='bg-[#112240] border border-[#00E5FF]/40 rounded-xl p-8 max-w-4xl mx-auto text-center shadow-lg'>\n"
            f"      <div class='text-xs font-mono text-[#00E5FF] font-bold tracking-wider mb-2'>INDIAN NAVAL STAFF BRIEFING</div>\n"
            f"      <h1 class='text-3xl md:text-4xl font-extrabold text-white tracking-wide uppercase font-serif'>{title}</h1>\n"
            f"      {subtitle}\n"
            f"      <div class='mt-6 pt-6 border-t border-[#233554] flex justify-around text-xs text-slate-300 font-mono'>\n"
            f"        <div><span class='text-slate-400'>PRESENTER:</span> <strong class='text-white'>{officer}</strong></div>\n"
            f"        <div><span class='text-slate-400'>COMMAND:</span> <strong class='text-white'>{unit}</strong></div>\n"
            f"      </div>\n"
            f"    </div>"
        )

    def _render_bluf_html(self, item: SlideItem) -> str:
        content: BLUFSlideContent = (
            item.content if isinstance(item.content, BLUFSlideContent)
            else BLUFSlideContent.model_validate(item.content)
        )
        slide_title = html.escape(item.title or "EXECUTIVE SUMMARY (BLUF)")
        headline = html.escape(content.bluf_headline)
        decision = html.escape(content.decision_requested)
        risk = f"<div class='mt-4'><span class='text-xs font-bold font-mono text-red-400 uppercase'>OPERATIONAL RISK:</span><p class='text-sm text-slate-300 mt-1'>{html.escape(content.risk_summary)}</p></div>" if content.risk_summary else ""

        takeaways_li = "\n".join(
            f"          <li class='text-sm text-slate-200 leading-relaxed'>• {html.escape(t)}</li>"
            for t in content.key_takeaways
        )

        return (
            f"    <div class='w-full'>\n"
            f"      <h2 class='text-xl font-bold text-white mb-4 tracking-wide border-l-4 border-[#00E5FF] pl-3'>{slide_title}</h2>\n"
            f"      <div class='grid grid-cols-1 md:grid-cols-12 gap-6'>\n"
            f"        <!-- Left Column: BLUF & Takeaways -->\n"
            f"        <div class='md:col-span-7 bg-[#112240] p-5 rounded-lg border border-[#233554]'>\n"
            f"          <div class='text-xs font-mono font-bold text-[#FFD700] uppercase mb-1'>BOTTOM LINE UP FRONT</div>\n"
            f"          <p class='text-base font-semibold text-white mb-4'>{headline}</p>\n"
            f"          <div class='text-xs font-mono font-bold text-[#00E5FF] uppercase mb-2'>KEY FINDINGS & TAKEAWAYS</div>\n"
            f"          <ul class='space-y-2'>\n{takeaways_li}\n          </ul>\n"
            f"        </div>\n"
            f"        <!-- Right Column: Decision & Risk -->\n"
            f"        <div class='md:col-span-5 bg-[#112240] p-5 rounded-lg border border-[#233554] flex flex-col justify-between'>\n"
            f"          <div>\n"
            f"            <div class='flex justify-between items-center mb-2'>\n"
            f"              <span class='text-xs font-mono text-slate-400'>URGENCY</span>\n"
            f"              <span class='text-xs font-mono font-bold px-2 py-0.5 rounded bg-cyan-950 text-[#00E5FF] border border-[#00E5FF]/30'>{html.escape(content.urgency.value)}</span>\n"
            f"            </div>\n"
            f"            <div class='text-xs font-mono font-bold text-[#FFD700] uppercase mt-2'>DECISION REQUESTED</div>\n"
            f"            <p class='text-sm font-medium text-white mt-1'>{decision}</p>\n"
            f"            {risk}\n"
            f"          </div>\n"
            f"        </div>\n"
            f"      </div>\n"
            f"    </div>"
        )

    def _render_policy_matrix_html(self, item: SlideItem) -> str:
        content: PolicyMatrixSlideContent = (
            item.content if isinstance(item.content, PolicyMatrixSlideContent)
            else PolicyMatrixSlideContent.model_validate(item.content)
        )
        slide_title = html.escape(item.title or "REGULATORY POLICY MATRIX")
        precedence = f"<div class='mt-3 text-xs font-mono text-[#FFD700]'>STATUTORY PRECEDENCE: {html.escape(content.statutory_precedence_note)}</div>" if content.statutory_precedence_note else ""

        headers_th = "".join(
            f"<th class='p-2.5 text-left text-xs font-mono font-bold text-[#00E5FF] bg-[#112240] border-b border-[#233554]'>{html.escape(h)}</th>"
            for h in content.headers
        )

        num_cols = len(content.headers)
        rows_tr = []
        for r in content.rows:
            row_items = [r.row_title] + r.cells if len(r.cells) == num_cols - 1 else r.cells
            tds = "".join(
                f"<td class='p-2.5 text-xs text-slate-200 border-b border-[#233554]/60 { 'font-semibold text-white' if c_idx == 0 else '' }'>{html.escape(val)}</td>"
                for c_idx, val in enumerate(row_items[:num_cols])
            )
            rows_tr.append(f"<tr class='hover:bg-[#112240]/40 transition-colors'>{tds}</tr>")

        rows_html = "\n".join(rows_tr)

        return (
            f"    <div class='w-full'>\n"
            f"      <h2 class='text-xl font-bold text-white mb-3 tracking-wide border-l-4 border-[#00E5FF] pl-3'>{slide_title}</h2>\n"
            f"      <div class='overflow-x-auto rounded-lg border border-[#233554] bg-[#0A192F]'>\n"
            f"        <table class='w-full border-collapse'>\n"
            f"          <thead><tr>{headers_th}</tr></thead>\n"
            f"          <tbody>\n{rows_html}\n</tbody>\n"
            f"        </table>\n"
            f"      </div>\n"
            f"      {precedence}\n"
            f"    </div>"
        )

    def _render_financial_delegation_html(self, item: SlideItem) -> str:
        content: FinancialDelegationSlideContent = (
            item.content if isinstance(item.content, FinancialDelegationSlideContent)
            else FinancialDelegationSlideContent.model_validate(item.content)
        )
        slide_title = html.escape(item.title or f"DFPDS SCHEDULE {content.schedule_no:02d} DELEGATIONS")
        notes = f"<div class='mt-3 text-xs font-mono text-slate-400'>STATUTORY PROVISO: {html.escape(content.notes)}</div>" if content.notes else ""

        tier_rows = []
        for t in content.tiers:
            with_ifa = f"₹{t.with_ifa_limit:.2f} Cr" if t.with_ifa_limit > 0 else "Nil / Full"
            without_ifa = f"₹{t.without_ifa_limit:.2f} Cr" if t.without_ifa_limit > 0 else "Nil"
            pac = f"₹{t.pac_limit:.2f} Cr" if t.pac_limit is not None and t.pac_limit > 0 else "—"

            tier_rows.append(
                f"<tr class='hover:bg-[#112240]/50 border-b border-[#233554]/50'>\n"
                f"  <td class='p-2 text-xs font-mono text-cyan-400 font-bold'>{html.escape(t.tier)}</td>\n"
                f"  <td class='p-2 text-xs text-white font-medium'>{html.escape(t.tier_name)}</td>\n"
                f"  <td class='p-2 text-xs text-right text-[#FFD700] font-bold font-mono'>{with_ifa}</td>\n"
                f"  <td class='p-2 text-xs text-right text-slate-300 font-mono'>{without_ifa}</td>\n"
                f"  <td class='p-2 text-xs text-right text-slate-400 font-mono'>{pac}</td>\n"
                f"</tr>"
            )

        tier_html = "\n".join(tier_rows)

        return (
            f"    <div class='w-full'>\n"
            f"      <h2 class='text-xl font-bold text-white mb-3 tracking-wide border-l-4 border-[#00E5FF] pl-3'>{slide_title}</h2>\n"
            f"      <div class='overflow-x-auto rounded-lg border border-[#233554] bg-[#0A192F]'>\n"
            f"        <table class='w-full border-collapse'>\n"
            f"          <thead>\n"
            f"            <tr class='bg-[#112240] text-left text-xs font-mono font-bold text-slate-300 border-b border-[#233554]'>\n"
            f"              <th class='p-2 text-[#00E5FF]'>TIER</th>\n"
            f"              <th class='p-2'>COMPETENT FINANCIAL AUTHORITY</th>\n"
            f"              <th class='p-2 text-right text-[#FFD700]'>WITH IFA</th>\n"
            f"              <th class='p-2 text-right'>WITHOUT IFA</th>\n"
            f"              <th class='p-2 text-right'>PAC LIMIT</th>\n"
            f"            </tr>\n"
            f"          </thead>\n"
            f"          <tbody>\n{tier_html}\n</tbody>\n"
            f"        </table>\n"
            f"      </div>\n"
            f"      {notes}\n"
            f"    </div>"
        )
