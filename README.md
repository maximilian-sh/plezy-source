# Plezy source

AltStore/Feather source for the official [Plezy](https://github.com/edde746/plezy) iOS IPA.

Add to Feather / AltStore / SideStore:

```
https://raw.githubusercontent.com/maximilian-sh/plezy-source/main/source.json
```

## How it works

A GitHub Action runs once a day (06:00 UTC) and runs `build_source.py`, which:

- rebuilds `source.json` from scratch from the GitHub releases of `edde746/plezy` (no state carried over)
- only accepts `downloadURL`s of the form `https://github.com/edde746/plezy/releases/download/<tag>/plezy-ios.ipa`
- takes the SHA-256 from the digest GitHub computed when the asset was uploaded
- downloads the newest IPA and checks its hash, size and bundle ID (`com.edde746.plezy`)
- uses Python's standard library only, and the one Action it uses (`actions/checkout`) is pinned to a commit SHA
