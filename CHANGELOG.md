# v1.2.1 - 25-Jun-2024

## Changed

- Changed video thumbnails to be uploaded to facebook instead of using the google thumbnail link which was temporary.

## Fixed

- Fixed the carousels checkStatus function not triggering.

# v1.2.0 - 19-Jun-2024

## Milestones

- Rob should be feature-complete now and will enter feature freeze. No further features will be added to Rob by Richard.
- v1.2.0 will be the last major update to Rob by Richard.
- All future updates will be bug fixes.

## Added

- Added support for creating carousel ads.

## Changed

- Separated dev and prod versions of addToQueue functions.
    - Dev should be for testing new code.
    - Prod should be what the growth team uses.
- Changed the tables in the collab file template for hopefully the last time.
    - Added a new table for carousel ads.

# v1.1.0 - 12-Jun-2024

## Milestones

## Added

- Add support for uploading videos as ad media.
- Add support for creating video ads.

## Removed

- Removed the Rob_FB_Media sheet from use.

## Changed

- Changed the table format in the FB Adcopies sheet to support video ads.
- Moved the creation of Ad Creatives from fbAds functions to fbMedia functions.

## Fixed

- Fixed the bug in fbAds-addToQueue that caused Rob to crash when trying to create ads.
