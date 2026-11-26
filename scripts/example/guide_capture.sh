# Helpers for the install guide's screenshots (source this file in bash/zsh on macOS). Only windows these helpers open
# are captured, never the whole screen: the user's other windows stay out of the frame.
#   W=$(tnew)            a Terminal window with a clean HOME (work/guide/home) and a short prompt: no user or Mac name
#   trun $W "command"    run a command in it (it also types into a running program: stop programs first)
#   tbusy $W / ttext $W  is something running / the window's text (check it for paths before shooting)
#   tshot $W name        capture that window only → work/guide/raw/name.png
#   winid "App name"     window ids of another app (QuickTime Player, TextEdit, Google Chrome; macOS may use local names)
# Then: npm run guide:shots (cuts the title bar, blurs what src/guide/shots.json lists).
KIT="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/../.." && pwd)"
RAW="$KIT/work/guide/raw"; GHOME="$KIT/work/guide/home"
mkdir -p "$RAW" "$GHOME"
tnew() {
  osascript -e "tell application \"Terminal\"
    do script \"export HOME='$GHOME'; export PROMPT='%1~ %# '; unset RPROMPT; cd ~; clear\"
    delay 1.5
    set wid to id of front window
    set bounds of window id wid to {40, 40, 1000, 700}
    return wid
  end tell"
}
trun() { osascript -e "tell application \"Terminal\" to do script \"$2\" in tab 1 of window id $1" >/dev/null; }
tbusy() { osascript -e "tell application \"Terminal\" to busy of tab 1 of window id $1"; }
ttext() { osascript -e "tell application \"Terminal\" to contents of tab 1 of window id $1"; }
tshot() { screencapture -x -o -l "$1" "$RAW/$2.png"; }
winid() { swift "$KIT/scripts/example/winid.swift" "$1"; }
