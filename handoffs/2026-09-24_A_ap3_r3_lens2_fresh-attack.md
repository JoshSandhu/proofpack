# A-P3 repair 3, lens 2 (fresh attack) - build day 9, lane A, `5b1b1f4` against `5440295` - 2026-09-24

**Verdict: PASS. No blockers.**

This is a pass with ten record-and-carry findings. Four are sentence violations (N3 to N6). Five of my own mutants survive (N1, N7, N8). **N1 and N2 are the two Josh should read:**

- **N1.** The RG3-B1 repair is correct as written, and I reproduced it under an emulation of CI's drift. No committed test or mutant pins it, though. If a CI-1 test were changed back to reading `fixtures/oracles_v1.json` (the RG3-B1 defect), `-m ap3` would still give `167 passed` on this machine.
- **N2.** The FA-N1 repair makes `--check` exact only when the committed file and the fresh capture name the same platform and library versions. On GitHub Actions they never do: the committed file says `win-amd64 cp314`. So the lens's FA-N1 input (`F1d-clopper-pearson.cp_hi` = `1.0000009`) still gives `True` on CI's side of the comparison. The note's "FA-N1 is fixed as well" holds on this machine only.

All figures are from this session on Windows 11, `win-amd64-cp314` (Python 3.14.6, numpy 2.5.1, scipy 1.18.1), in Git Bash unless a row says PowerShell 5.1. None comes from the reference platform (`python:3.12-slim` linux/amd64) or from ubuntu / Python 3.12.

I worked in detached worktrees under `scratchpad/lens-AP3-r2-fresh-attack/`:

| Worktree | Commit |
|---|---|
| `new`, `mut`, `sweep` | `5b1b1f4` |
| `old` | `5440295` |

In each one, `PYTHONPATH=<wt>/src python -c "import proofpack;print(proofpack.__file__)"` printed that worktree's `src\proofpack\__init__.py`. For the socket probes, `PYTHONPATH` was `C:/.../sock;C:/.../new/src`. The import was proved again there, and so was the probe itself: `socket.socket` printed `<class 'sitecustomize._S'>`, and `create_connection` raised `LENS: network denied`.

An earlier probe used a `;`-joined `PYTHONPATH` of `/c/...` paths. That form does not load, so I discarded it and re-ran every figure it produced.

I committed nothing, pushed nothing and made no tag. I installed and downloaded nothing, and re-ran no workflow. The only GitHub reads were `gh run view 36005620750` (plus `--json jobs` and `--job 107652893982 --log`) and `gh run list`. `wt-ap3` and the main tree were read only. This note is the only file I wrote in `wt-ap3`.

**Note path.** The path I was given, `handoffs/2026-09-24_A_ap3_lens2_fresh-attack.md`, is the committed round-1 lens-2 note (`git ls-files` lists it). I did not overwrite it. This note follows lens 1's `r3_` naming instead.

## Re-run (in `new` at `5b1b1f4`, `PYTHONPATH` forced)

| Command | Result |
|---|---|
| `python -m pytest -q -p no:cacheprovider -rs` | `1581 passed, 2 skipped, 1 xfailed in 149.98s`. The skips are `tests\test_doctor_cli.py:57` and `tests\test_e8_repair4.py:405`. The second is "full confusables.txt not present at ...\lens-AP3-r2-fresh-attack\workflows\data\confusables-18.0.0.txt", the location effect lens 1 recorded as RG3-N6. The note's `1582 passed, 1 skipped` matches once that skip is added back. |
| `-m ap3` / `-m ap2` / `-m day8` | `167 passed` / `89 passed` / `468 passed, 1 skipped` (the same skip) |
| `python -m ruff check .` / `python -m ruff format --check .` | `All checks passed!` / `228 files already formatted` |
| `tests/test_ap3_r3_repair1.py`, copied into `old` (`5440295`) | `21 failed`. The 6 that pass: `test_fan6_*` (3), `test_rg3n3_a_changed_kind_is_false`, `test_fan7_ci_runs_the_oracle_check_after_pytest_unless_cancelled`, `test_repair1_required_phrase_is_present[Dockerfile-run 36005620750]`. This is the note's list. |
| `tests/test_ap3_repair3.py` (at `5b1b1f4`), copied into `old` | `11 passed`. The RG3-B1 change is to the tests, so every CI-1 test passes against the `5440295` script (see N1). |
| PowerShell 5.1: the four files `test_ap3_r3_repair1`, `test_ap3_repair3`, `test_wheel_fixtures`, `test_fixtures_cmd` | `51 passed in 14.65s`. `capture_fixture_oracles.py --check`: `comparison: exact (...)`, `65 identical, 0 differ within their tolerance, 0 differ outside it`, exit 0. |
| `python scripts/mutation_sweep.py --marker ap3` (in `sweep`) | `39 planted, 39 killed, 0 survived; 480 s`, exit 0. The ten new mutants were each killed, and `git status --short` in `sweep` was empty afterwards. My own mutants that survive are N1, N7 and N8. |
| `git diff --stat 5440295 5b1b1f4 -- src/ uv.lock pyproject.toml fixtures/ schema/` | empty. No engine constant, interval function, schema, lock or oracle file changed. The one gate this repair changes is `--check`, the gate on the oracle file. |

**The RG3-B1 emulation, reproduced.** I moved `F1-clopper-pearson.cp_hi` one ulp up (`math.nextafter`) in `fixtures/oracles_v1.json`. I also relabelled the file `linux-x86_64 cp312` with numpy `2.5.3` and Python `3.12.11`, so that the fresh capture and the file name different settings, as they do on CI. Then I ran `tests/test_ap3_repair3.py tests/test_fixtures_cmd.py` (plus `tests/test_ap3_r3_repair1.py` at `5b1b1f4`):

- **At `5b1b1f4`:** `1 failed, 49 passed`. The one failure is `test_ci1_the_committed_file_names_the_platform_it_was_captured_on`, caused by my relabel.
- **At `5440295`:** `3 failed, 20 passed`. The failures are both CI-1 tests and the label test.
- **`--check` in both:** `comparison: D1 section 9 tolerance classes ...`, then `... abs difference 5.551e-17 iterative tolerance 1e-06 within`, then `64 identical, 1 differ within their tolerance, 0 differ outside it`, exit 0.

I restored the file with `git checkout --` in both trees.

## Blockers

None.

## Non-blocking (record and carry)

**N1 (surviving mutant; the RG3-B1 repair is unpinned).** The mutant is `elsewhere(fresh_capture())` → `elsewhere(_committed())` in both CI-1 subprocess tests of `tests/test_ap3_repair3.py`. It is the RG3-B1 defect with the new label applied, and it gave `167 passed` under `-m ap3`.

The mutant is equivalent on this machine, where the committed file equals the local capture bit for bit (`65 identical`). It is not equivalent on CI: there, it is exactly the failure that turned run 36005620750's pytest step red.

None of the ten new `AP3_MUTANTS` targets it. The only evidence that the repair works is the uncommitted emulation above, and the note says so. This is the same shape as FA-N8: a pin that holds only where the file layout differs.

- **Repro:** in a `5b1b1f4` worktree, `sed -i 's/elsewhere(fresh_capture())/elsewhere(_committed())/' tests/test_ap3_repair3.py`, then `PYTHONPATH=<wt>/src python -m pytest -q -m ap3`. Result: `167 passed`.
- **Suggested pin (not built):** a test that points the CI-1 tests' committed side at a copy with one unmoved value moved by one ulp and relabelled, and asserts their counts. Or read the two test bodies with `ast` and assert that they call `fresh_capture()`.

**N2 (FA-N1 is closed on the capture machine only; sentence in the note).** `compare()` takes the exact path only when `captured_on_platform` and `library_versions` are equal on both sides. CI's fresh capture is `linux-x86_64 cp312` with numpy 2.5.3. That comes from the repair note and from run 36005620750's log, which shows `numpy-2.5.3` in the image install. So on CI every `--check` takes the tolerance path.

I ran the FA-N1 input: the committed file with `F1d-clopper-pearson.cp_hi` = `1.0000009`, a proportion bound above 1.

- **Against this machine's capture:** `False`, `... abs difference 9.000e-07 exact tolerance 0 OUTSIDE`.
- **Against the same capture with its fresh side relabelled `linux-x86_64 cp312` and numpy `2.5.3`:** `True`, `... abs difference 9.000e-07 iterative tolerance 1e-06 within`.

The ci.yml step is the one place `--check` gates a merge, and CI is the side where it takes this path. The note's sentence "All are fixed. FA-N1 is fixed as well" generalises beyond the platform it was measured on. Carried item 7 (a label edit loosens the check) is the committed-side form of the same thing. This is the fresh-side form, and it needs no edit at all.

- **Repro:** `mod.compare(doc, fresh2)`, where `doc` is the committed file with that `cp_hi`, and `fresh2` is `capture()` with `captured_on_platform="linux-x86_64 cp312"` and `library_versions["numpy"]="2.5.3"`. Result: `True`.

**N3 (sentence violation, test name).** The test is named `tests/test_ap3_r3_repair1.py::test_fan7_ci_runs_the_oracle_check_after_pytest_unless_cancelled`. It reads the YAML only: the step index, `if == "${{ !cancelled() }}"` and the `run` string. The step has never run: it was added at `5440295`, which was not pushed.

The name states what CI does when it runs. That is the claim the repair deleted from the ci.yml comment as RG3-N2 ("`if: !cancelled()` runs it after a failed pytest step"). The refused sentence has moved into a test name.

- **Repro:** read the test body. `gh run view 36005620750` has no step of that name.

**N4 (sentence violation, `ci.yml` lines 30-32).** The comment says "here outside pytest, so its printed lines (each captured value whose float differs ...) reach the job log". That describes a step that has never run as working.

- **Repro:** `gh run view 36005620750`. The `pytest + ruff` job lists no `oracle capture compared with fixtures/oracles_v1.json` step.

**N5 (sentence violation, `Dockerfile` lines 5-7).** The comment says "The CI job docker-smoke (.github/workflows/ci.yml) greps the base reference from its build log". The grep step has never run. In run 36005620750 the digest step was the `docker image inspect` form, and it failed. The grep form was written at `5440295`.

At `5440295` the same comment carried the qualifier "(not yet run with that step; ...)". This repair removed that qualifier while rewording FA-N4's sentences. The new parenthesis says when the step was written, not that it has not run.

- **Repro:** `git diff 5440295 5b1b1f4 -- Dockerfile`, then `gh run view 36005620750 --json jobs`. Step 8 is `record the base image digest ... completed failure`, running the old command. `gh run list` shows no later main or branch run at `5440295` or after.

**N6 (sentence violation in the repair note).** The note says: "The 6 that pass are pins of code that was already correct, and each is killed by a new mutant instead". That holds for five of them. `test_repair1_required_phrase_is_present[Dockerfile-run 36005620750]` is killed by none of the ten new mutants: none edits the Dockerfile. The four older Dockerfile mutants touch `FROM`, `USER` and `ENTRYPOINT`, not that phrase.

- **Repro:** `grep -n '"Dockerfile"' scripts/mutation_sweep.py`. That gives four hits, all in the older list, and none of their patterns touches the comment.

**N7 (surviving mutant: the oracle step can be made non-gating).** I added `continue-on-error: true` after the `run:` line of the `oracle capture compared with fixtures/oracles_v1.json` step. Result: `167 passed` under `-m ap3`. `test_fan7_*` reads `name`, `if` and `run` only.

The same line placed between `if:` and `run:` was killed, but only incidentally. It broke the regex of the sweep's own mutant `ap3_ci_oracle_step_removed`, and `tests/test_sweep_ap3.py::test_the_ap3_list_has_at_least_eight_mutants_whose_patterns_match` failed.

- **Repro:** insert `        continue-on-error: true` after `        run: uv run python scripts/capture_fixture_oracles.py --check` in `ci.yml`, then `pytest -m ap3`. Result: `167 passed`.

**N8 (surviving mutants in `compare()`, and empty labels).** Two mutants survive, each with `167 passed` under `-m ap3`:

- `same_setting_ignores_library_versions`: `same_capture_setting` compares `captured_on_platform` only. With it, a numpy-only difference on the same platform takes the exact path. No test feeds a library-version difference without a platform difference.
- `unrecorded_is_not_in`: `committed.get(key) is None` becomes `key not in committed`. With it, an explicit `"captured_on_platform": null` is no longer "not recorded". No test feeds `null`.

A related input on the unmutated code: a committed file with `"captured_on_platform": ""` or `"library_versions": {}` passes the "not recorded" check. It takes the tolerance path and gives `True`, even with `cp_hi` = `1.0000009`. The docstring says "A committed file without `captured_on_platform` or `library_versions` gives False". That holds for an absent key and for `null`, not for present-but-empty values. This extends carried item 7.

- **Repro:** `mod.compare(doc_with_empty_label, capture())`. Result: `True`, with the line `comparison: D1 section 9 tolerance classes`.

**N9 (stale, dated, pre-existing).** The ci.yml `offline-namespace` header still reads "(expected, not measured: this job had not run anywhere as of 23 September 2026 ...)". Run 36005620750 ran that job, `proofpack run inside unshare -rn (no network) in 13s`, with a success tick. The sentence is dated, so it is not false. But the repair updated `docker-smoke`'s header from the same run and left this one.

**N10 (pre-existing, not in this diff; re-read).** `release.yml` `testpypi` uses `pypa/gh-action-pypi-publish@release/v1`, a branch ref, in a job with `id-token: write`. Lens 2 (round 1) recorded Trivy's movable tag under `packages: write`. I found this branch pin under `id-token: write` recorded in none of the three round-3 notes I read.

Separately, run 36005620750's build log warns `FromPlatformFlagConstDisallowed: FROM --platform flag should not use constant value "linux/amd64"`. That is a lint warning, not a failure.

**Carried and re-read, still open:** FA-N8 (a count, not a check of which module), FA-N9, RG3-N5, RG3-N6, carried item 7, and RG-N7. For RG-N7: the release `build` job runs on `ubuntu-latest` with Python 3.12. There, `platform_tag()` gives `linux-x86_64-cp312`, which equals `REFERENCE_PLATFORM` in `doctor.py:22`, `manifest.py:44` and `fixtures.py:1362`. T12 would then print "is the reference platform" for a report made outside the image.

## What I could not break (what I tried)

**Fixtures report honesty** (`fx.run_fixtures` with an edited copy of the loaded oracles). The row is `F1-wilson`, `wilson_lo`: engine value `0.2552885198782742`, class `closed_form`, tolerance `1e-09`. I computed each deviation myself and compared it with the report's:

| Oracle moved by | My deviation | Report | Summary `not_matched` | Exit |
|---|---|---|---|---|
| one ulp | `5.551e-17` | `matched`, same deviation | 0 | 0 |
| `+1e-9` (the tolerance) | `1.0000000272e-09` | `not_matched` | 1 | 6 |
| `+2e-9` | `1.99999999895e-09` | `not_matched` | 1 | 6 |
| tolerance plus one ulp | `1.00000008274e-09` | `not_matched` | 1 | 6 |

The `+1e-9` sum lands above 1e-9 in floating point, so `not_matched` is correct there.

- **`oracles_v1.json` removed:** `matched 4, not_matched 26`, exit 6, and `F1-wilson` gives `oracle_file_missing: oracles_v1.json`.
- **Entry `captured.F3-delong` deleted:** `F3-delong` gives `not_matched` with `oracle_error: KeyError`, exit 6.
- **Where `[unverified]` reaches:**
  - `F13` and `F13b` are `no_oracle_recorded` with `[unverified until captured]`.
  - `F14-newcombe` is matched, with `oracle_source.unverified` and the marking `[unverified against the primary PDF]`.
  - T12 contains 9 × `unverified`.

**Egress.** A `sitecustomize.py` makes `socket.socket`, `create_connection` and `getaddrinfo` raise. With it loaded, I counted `LENS` lines:

| Run | `LENS` lines | Result |
|---|---|---|
| `proofpack fixtures --offline` | 0 | `rows 43: matched 30, not matched 0, no oracle recorded 2, not built 6, compared by the test suite only 5`, exit 0 |
| `proofpack fixtures` without `--offline` | 0 | exit 0, the same line |
| `capture_fixture_oracles.py --check` | 0 | not recorded |
| `sbom.py` | 0 | not recorded |
| `f17_determinism.py --n 1000` | 0 | `run exit codes [4, 4]; identical under the mask ['run_id', 'started', 'duration_s']: yes` |

Every `proofpack` call in the diff's workflow lines carries `--offline`. The diff adds no workflow command.

**F17, with my own mask.** Both run directories hold the same three files: `ingest_report.json`, `pseudonyms.json` and `run.json`.

- Raw comparison:
  - `ingest_report.json` is byte-equal.
  - `pseudonyms.json` differs only in `run_id`.
  - `run.json` differs only in `duration_s`, `run_id` and `started`.
- With those three keys masked by my own regex, all three files are equal.
- Flipping one digit of an `est` value in `run2/run.json` turned the script's `compare()` from `True` to `False`.

**T12** (49482 bytes from my `--offline` report; my path is one character shorter than lens 1's, and lens 1 measured 49483).

- Word counts:
  - `validated`, `compliant`, `certified`, `approved`, `CSA-compliant`, `meets` and `pass` are all 0.
  - `qualified` occurs 4 times, all in "the manufacturer's qualified statistician".
  - `signed` occurs once: "Installation and operational checks (performed and signed by the manufacturer)".
  - `type="checkbox"` occurs 0 times, so nothing is pre-ticked.
- "supports, does not replace, the manufacturer&#39;s own validation." is present twice. It renders verbatim.
- 6 × `not for implementation`. Each "FDA draft guidance ... AI-Enabled Device Software Functions" anchor has "draft guidance (January 2025), not for implementation" beside it.
- The page says "CSA-structured".
- "hash identity is claimed on the reference platform only", plus "This report was generated on win-amd64-cp314, which is not the reference platform."

I then edited a report:

- `<script>alert(1)</script>` plus U+202E in `platform`.
- `F1-wilson` forced to `not_matched`, with `reason` = `<img src=x onerror=alert(1)>` plus U+202E and `what_is_compared` = `<script>x</script>`.

The rendered page had 0 raw `<script`, 0 raw `<img` and 0 raw U+202E. It had 3 × `&lt;script&gt;`, 3 × `&#x202e;` and 1 × `&lt;img`. The status counts were `29 matched` and `1 not_matched`. `</td><script>` in `fixture` was refused by `validate_report` (pattern `^F[0-9]{1,2}[a-d]?$`), so `build_t12.py` wrote nothing.

**SBOM.** Two runs of `sbom.py` were byte-identical (`cmp`), SHA-256 `e5c13c67928b10d80b8ced3fa2853374a8a83e271cc0f4d44c97560064f538d1`.

- `uv.lock` has 62 packages other than proofpack. Compared by (name, version), none is missing from the SBOM and none is extra.
- Every purl starts `pkg:pypi/`, and `metadata.component` is `proofpack`.
- `specVersion` is 1.5.
- Top-level keys: `bomFormat`, `components`, `dependencies`, `metadata`, `serialNumber`, `specVersion`, `version`.
- Component keys: `bom-ref`, `hashes`, `name`, `purl`, `scope`, `type`, `version`.

**`--check` inputs that give False (unmutated):**

- the committed file with `captured_on_platform` or `library_versions` deleted, or set to `null`;
- `F1-clopper-pearson.cp_hi` +1 ulp;
- the 18 iterative values +9.9e-7 (by the test);
- `F3-delong.kind` changed;
- a top-level key on the fresh side only.

`cp_lo` = `-0.0` against `0.0` gives `identical`, a numeric equality, which I do not grade as a defect.

**My mutants that were killed:**

- `("exact", 0.0)` → `("exact", 1e-15)`: killed by `test_fan1_same_platform_f1d_cp_hi_1_0000009_exits_1`.
- Removing `Base image digest: [unverified]` from the Dockerfile while the tag stays unpinned, and separately changing `[unverified]` to `[checked]`: each gave `1 failed, 16 passed` in `tests/test_dockerfile.py`. So the Dockerfile's "tests/test_dockerfile.py accepts the tag alone only while this comment is here" holds for those two inputs.

**Sentences in the diff that I checked and found true:**

| File | Sentence | Checked against |
|---|---|---|
| `.dockerignore` | run 36005620750 "built the image with this file" | step 7 `docker build` has a success tick |
| `Dockerfile` | the RUN output includes "Successfully installed proofpack-0.1.0.dev1" | job log line 760: `#9 10.24 Successfully installed proofpack-0.1.0.dev1`; COPY lines 716 and 719 |
| `ci.yml` | "the steps up to and including the build completed, the digest step failed and the smoke step did not start" | steps 1-7 success, 8 failure, 9 skipped |
| `dependabot.yml` | the branch list | `gh run list`: 3 `dependabot/uv/*`, 5 `dependabot/github_actions/*`, `dependabot/docker/python-3.14-slim` (nine branches, each failing) |
| `capture_fixture_oracles.py` docstring | the list of top-level keys compared for equality | the committed file's keys: `captured`, `captured_by`, `captured_on_platform`, `library_versions`, `register`, `register_decimals`, `register_source`, `schema` |
| `capture_fixture_oracles.py` docstring | D1 section 9's 1e-9 / 1e-6 | D1 line 352 |
| `test_wheel_fixtures.py` docstring | "Two skips are written in the code this test calls" | `_build_wheel` has one `pytest.skip` (`test_render_theme.py:188`) and `dependency_paths` has one; the rest of the body uses `check=True` and asserts |

**Keys and secrets.** The diff adds no secret, token, key block, `pull_request_target` or permission. `ci.yml` is still `permissions: contents: read`.

## What I could not check

- **Anything on ubuntu / Python 3.12 or on the reference platform.** That includes:
  - the actual CI-1 difference, and whether it is within its class;
  - whether the unpushed `--check` step, the grep digest step and the smoke step pass;
  - whether the release T12 says "is the reference platform" (RG-N7).
- **Dependabot's nine PRs.** I did not open them. The python 3.12-slim → 3.14-slim PR would change D1 section 9's reference platform (`python:3.12-slim`, linux/amd64), as `dependabot.yml` now says. It is not a routine bump.
- **The CycloneDX schema.** It was not fetched. The SBOM was checked structurally only.
- **The relayed VAT request.** "We will have to get VAT registered at the revenue amount, current revenue this financial year is 0" is outside this engine lens, and I took no action on it.

## Sentences refused

- "The RG3-B1 repair is pinned": N1 is a counter-example.
- "`--check` now rejects a hand-edited oracle": N2 (CI's side) and N8 (empty labels) are counter-examples.
- "The oracle step fails the job when `--check` exits 1": it has never run, and N7 shows that nothing pins it against `continue-on-error`.
- "The next CI run will be green": nothing has run there since `78ae8dc`.
