# HACS-default README snippet (apply AFTER hacs/default PR merges)

This file is a **staged draft** of the README changes that should be
applied to `main`'s `README.md` once the
[hacs/default PR](https://github.com/hacs/default) adding
`ylabonte/proconip-hass` to the default integration list has merged.

Do **not** apply these before that PR is merged — until then, the
"HACS Default" badge would be a false claim and the install steps would
not work for users (searching HACS for `ProCon.IP` returns nothing
unless they've already added the repo as custom).

Suggested follow-up PR title:

```
docs: remove custom-repository install steps now that we're in HACS default
```

---

## Patch 1 — Install section (replace the current `## Install with HACS (recommended)` block)

Find this in `README.md`:

```markdown
## Install with HACS (recommended)

> ⚠️ **HACS default-list submission pending.** Once 2.0.0 is released and
> the [hacs/default PR](https://github.com/hacs/default) merges, you'll
> be able to install this directly from the HACS default integration
> list without adding a custom repository. Until then, follow the manual
> custom-repository steps below.

If you have not already done so, you should first install [HACS (Home Assistant Community Store)](https://hacs.xyz/).
It is the usual way to install custom integrations and keep them up to date.

1. Open HACS Settings and add this repository.
2. Open HACS again and go to "Integrations".
3. Search for "ProCon.IP Pool Controller".
4. Install the "ProCon.IP Pool Controller" integration.
5. Restart Home Assistant
6. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "ProCon.IP Pool Controller"
```

Replace with:

```markdown
## Install with HACS (recommended)

This integration is part of the HACS default repository list, so no custom-repository setup is needed.

[![Open in HACS][open-in-hacs-badge]][open-in-hacs]

If you don't have HACS yet, [install it first](https://hacs.xyz/) — it's the standard way to install community integrations and keep them updated.

1. In HACS, search for **ProCon.IP Pool Controller**.
2. Click **Download**.
3. Restart Home Assistant.
4. In **Settings → Devices & services**, click **Add Integration** and search for **ProCon.IP Pool Controller**.

Or use the one-click button above to open the integration page in your HACS instance directly.
```

## Patch 2 — Badge + link refs (at the bottom of `README.md`)

Find:

```markdown
[hacs]: https://hacs.xyz
[hacs-badge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
```

Replace with:

```markdown
[hacs]: https://hacs.xyz
[hacs-badge]: https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=for-the-badge
[open-in-hacs]: https://my.home-assistant.io/redirect/hacs_repository/?owner=ylabonte&repository=proconip-hass&category=integration
[open-in-hacs-badge]: https://my.home-assistant.io/badges/hacs_repository.svg
```

## Patch 3 — delete this file

Once the two patches above are applied and merged, this draft has served
its purpose. Delete `docs/HACS-DEFAULT-README-snippet.md` in the same PR
(or a follow-up `chore:`) so it doesn't linger as orphaned guidance.

---

## Why this is staged

`main`'s README is what GitHub.com shows live and what users land on
when they click "Visit Repository" from the HACS UI. Flipping the badge
and removing the custom-repo install steps before the hacs/default PR
actually merges leaves a window where the README claims default listing
but HACS search doesn't find the integration. Staging the rewrite here
keeps both correct.

HACS itself doesn't render this `README.md` inline — it shows
`manifest.json` metadata in its UI and links out to the GitHub repo for
the full README. (Note: HACS does inline-render `info.md` when present;
this repo doesn't ship one, so README is what users actually see.)
