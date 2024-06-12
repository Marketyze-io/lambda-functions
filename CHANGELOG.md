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

## Known Issues

- Deleting/resetting a collab file saved in Rob is not possible through Rob.
- All previous versions of the collab file will not work with Rob anymore.
- Rob currently cannot update existing collab files to the latest version. You need to make a new copy of the v4 template.
