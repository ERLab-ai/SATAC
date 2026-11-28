# A07 — Exact embedded URL access candidate

An explicit curator decision withholds structured legacy records containing the exact URL as a JSON string, regardless of whether it has been registered as a SourceVersion. It does not rewrite or strip nested fields. The rule applies in the common masked public projection to all release reads, including archives. Immutable release members and manifest hashes are unaffected. No actual access decision is applied.

The decision matches literal JSON string values only, not keys, URL aliases, redirects, substrings of prose or encoded variants. Curators must identify those separately and use whole-version withholding where appropriate. This is an enforcement control, not an automated licensing decision. Do not treat the candidate as verified before SQL/HTTP and regression results.
