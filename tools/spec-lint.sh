#!/usr/bin/env bash
# Lint all specs and DEB recipes in one clean Tumbleweed container.
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 2
IMG="${1:-registry.opensuse.org/opensuse/tumbleweed:latest}"
docker run --rm -v "$PWD":/work -w /work "$IMG" bash -lc '
  set -uo pipefail
  ok=0
  for i in 1 2 3; do zypper --non-interactive --gpg-auto-import-keys refresh >/tmp/zr 2>&1 && ok=1 && break; sleep 3; done
  if [ "$ok" != 1 ]; then
    zypper --non-interactive removerepo repo-oss repo-update repo-non-oss >/dev/null 2>&1
    zypper --non-interactive --gpg-auto-import-keys addrepo --refresh https://ftp.halifax.rwth-aachen.de/opensuse/tumbleweed/repo/oss/ oss-mirror >/dev/null 2>&1
    zypper --non-interactive --gpg-auto-import-keys refresh >/tmp/zr 2>&1 || { echo "SETUP_REFRESH_FAIL"; tail -3 /tmp/zr; exit 2; }
  fi
  zypper --non-interactive --gpg-auto-import-keys install -y rpm-build rpmlint spec-cleaner rpmdevtools zypper vim diffutils make >/tmp/zi 2>&1 || { echo "SETUP_TOOLS_FAIL"; tail -3 /tmp/zi; exit 2; }
  command -v rpmspec >/dev/null 2>&1 || { echo "SETUP_NO_RPMSPEC"; exit 2; }
  echo "zypper install PASS: rpm-build rpmlint spec-cleaner rpmdevtools (container toolchain)"
  total=0; bad=0; sc_ok=0; rl_ok=0; rs_ok=0
  for spec in */*.spec; do
    total=$((total+1))
    if rpmspec -P "$spec" >/dev/null 2>&1; then rs_ok=$((rs_ok+1)); else echo "RPMSPEC_FAIL $spec"; bad=$((bad+1)); fi
    rpmlint -i "$spec" >/tmp/rl 2>&1; r=$?
    if [ "$r" -le 1 ]; then rl_ok=$((rl_ok+1)); else echo "RPMLINT_FAIL $spec rc=$r"; head -5 /tmp/rl; bad=$((bad+1)); fi
    if command -v spec-cleaner >/dev/null 2>&1; then
      if spec-cleaner -d "$spec" >/tmp/sc 2>&1; then sc_ok=$((sc_ok+1)); else echo "SPEC_CLEANER_FAIL $spec"; bad=$((bad+1)); fi
    fi
  done
  for rules in */debian.rules; do
    make -n -f "$rules" >/dev/null 2>&1 || { echo "RULES_FAIL $rules"; bad=$((bad+1)); }
    grep -q "^#!/usr/bin/make -f" "$rules" || { echo "RULES_SHEBANG_MISSING $rules"; bad=$((bad+1)); }
  done
  echo "rpmspec -P PASS $rs_ok/$total"
  echo "rpmlint PASS $rl_ok/$total (rc<=1, spec-level warnings allowed)"
  echo "spec-cleaner PASS $sc_ok/$total"
  echo "spec-lint: $bad findings"
  [ "$bad" -eq 0 ]
'
echo "spec-lint rc=$?"
