# Herdr configuration

This directory provides a tmux-style Herdr setup for Linux and macOS:

- `config.toml` defines the `Ctrl-a` keymap and interface settings.
- `tmux-compat/` adds the pane picker, most-recent-tab switching, and clean copy
  view.

## Install

From the repository root, run `./install.sh` and select Herdr. The installer
uses Homebrew on macOS and a supported native package manager plus Herdr's
official release installer on Linux. If Herdr is missing, it asks before
installing it. Choosing skip still links the configuration; rerun the installer
after installing Herdr manually to validate the config and link the plugin.

For a manual Linux installation:

```sh
sudo apt-get install jq python3 curl
curl -fsSL https://herdr.dev/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
```

On macOS with Homebrew:

```sh
brew install herdr jq python
```

Then replace `/path/to/tmux` with the repository path and link the
configuration and plugin:

```sh
mkdir -p ~/.config/herdr
ln -sfn "/path/to/tmux/herdr/config.toml" ~/.config/herdr/config.toml
herdr plugin link "/path/to/tmux/herdr/tmux-compat" --enabled
herdr config check
herdr server reload-config
```

### Custom config path

Herdr uses `HERDR_CONFIG_PATH` as the complete config filename when it is set.
Export it before running the installer and whenever you start Herdr:

```sh
export HERDR_CONFIG_PATH="$HOME/.config/herdr-work/config.toml"
./install.sh
herdr
```

The installer creates the parent directory and links that path to this
repository's `herdr/config.toml`. Existing files are backed up before the link
is created. If the variable already points directly to the repository config,
no link is needed.

Start Herdr with `herdr`, or connect to a remote server with:

```sh
herdr --remote user@server
```

## Shortcuts

| Shortcut | Action |
| --- | --- |
| `Ctrl-a c` | Create a tab |
| `Ctrl-a /` | Split to the right |
| `Ctrl-a -` | Split below |
| `Ctrl-a h/j/k/l` | Move between panes |
| `Ctrl-a w` | Choose a workspace, tab, or pane |
| `Ctrl-a Tab` | Return to the most recently used tab |
| `Ctrl-a 1-9` | Select a tab by number |
| `Ctrl-a x` | Close a pane |
| `Ctrl-a z` | Zoom a pane |
| `Ctrl-a m` | Toggle clean pane copy view |
| `Ctrl-a r` | Reload the configuration |
| `Ctrl-a e` | Edit the configuration |

In the pane picker, use `j`/`k` to move, `h`/`l` to collapse or expand,
`Enter` to select, and `q` or `Escape` to cancel.

## Copy text

For Herdr copy mode, press `Ctrl-a Enter`, select with vi keys and `v`, then
press `y`. Remote sessions forward copied text through OSC 52 when the local
terminal permits clipboard access.

Clean copy view zooms the current pane, hides the sidebar, and temporarily
disables borders, scrollbars, and Herdr's mouse capture so normal terminal
selection works. Press `Ctrl-a m` again to restore the previous pane, sidebar,
collapsed-sidebar presentation, and mouse settings. The ordinary sidebar
button continues to leave its compact strip visible.

The helper works through Herdr's live configuration on both Linux and macOS;
it does not need a terminal-specific key binding. Remove this obsolete Ghostty
binding if it was added for an older version:

```ini
keybind = ctrl+a>m=text:\x01b\x01m
```

An application inside the pane can request mouse reporting independently of
Herdr. Hold Shift while selecting in such applications to use the terminal's
native selection bypass.
