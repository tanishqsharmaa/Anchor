"""
anchor.generate — Natural Language Generation, NLI Verification, and Certified Abstention
"""

from anchor.generate.synthesizer import Synthesizer
from anchor.generate.nli_gate import NLIGate, SentenceVerification
from anchor.generate.abstention import (
    CertifiedAbstention,
    RefusalPayload,
    RefusalReasonCode,
)
from anchor.generate.citation import (
    ByteAnchor,
    Citation,
    CitationAnchorer,
)

__all__ = [
    "Synthesizer",
    "NLIGate",
    "SentenceVerification",
    "CertifiedAbstention",
    "RefusalPayload",
    "RefusalReasonCode",
    "ByteAnchor",
    "Citation",
    "CitationAnchorer",
]
