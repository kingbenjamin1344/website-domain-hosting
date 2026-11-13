# GH MAX CORPORATION Website

The maintained site source lives in `src/`. The build generates the deployable
static site in `dist/`; the generated output is not edited by hand or committed.
No server or runtime JavaScript framework is required.

## Development

Requires Python 3.10 or later. No third-party packages are needed.

1. Edit page sources in `src/`.
2. Update shared markup in `src/components/` and content records in
   `src/data/`.
3. Generate the deployable HTML:

   ```powershell
   python scripts/build.py
   ```

4. Verify generated pages are current:

   ```powershell
   python scripts/build.py --check
   ```

Configure your static host to publish the `dist/` folder after building.
The build copies the required assets, stylesheets, scripts, and favicon into it.
Do not delete `scripts/build.py`: it assembles shared components and creates the
deployable site.

## Structure

- `src/pages/` and `src/index.html` contain page-specific content and metadata.
- `src/components/` contains the shared navigation, footers, and reusable cards.
- `src/data/` contains the page registry and structured product/review content.
- `scripts/build.py` assembles these into the static site in `dist/`.

Product and review records are currently read from local JSON files. If a
database is added later, the content-loading step can be replaced while keeping
the page components and generated HTML structure intact.
