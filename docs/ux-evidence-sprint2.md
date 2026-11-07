# TC-UX-01 Usability and Accessibility Evidence (NF-003)

| Item | Value |
|---|---|
| Test case | TC-UX-01 (requirement NF-003) |
| Date | 7 November 2026 |
| Code tested | `main` at `46c729c` (production build, `vite preview`), API on PostgreSQL |
| Method | Scripted Chromium (Playwright) at a 360 x 800 px viewport, device scale 2, signed in as a test student on a clean local database; pointer clicks were counted by the script, typing and Tab presses were not counted, as the requirement states |
| Environment note | Run on a local copy of the deployed code, not on the Render site. Screenshots are in `docs/ux-evidence/` |
| Result | **Pass** (observations below are improvements, not failures) |

## 1. No horizontal scroll at 360 px

The page width never exceeded the viewport (`scrollWidth` 360 against `clientWidth` 360) on all nine views checked.

| View | Result | Screenshot |
|---|---|---|
| Home (signed out) | Pass | `01-home-360.png` |
| Register | Pass | `02-register-360.png` |
| Sign in | Pass | `05-login-wrong-password-360.png` |
| Browse | Pass | `hs-Browse.png` |
| My Listings | Pass | `hs-My-Listings.png` |
| Add a Book form | Pass | `07-listing-form-360.png` |
| Requests | Pass | `hs-Requests.png` |
| Exchanges | Pass | `hs-Exchanges.png` |
| Profile | Pass | `hs-Profile.png` |

## 2. Click counts from the authenticated Browse page (limit 5)

| Flow | Clicks | Steps counted | Result |
|---|---|---|---|
| Enter the listing flow and submit it | 3 | My Listings, + Add a Book, Submit; fields filled by typing and Tab | Pass. If the first field is clicked instead of reached by keyboard the count is 4, still within 5. The listing "Compilers Principles" appeared in the list (`08-listing-submitted-360.png`) |
| Enter a query and display results | 2 | Browse Books, Search; the query is typed | Pass. The matching book appeared (`09-search-results-360.png`) |

## 3. Labelled inputs

Every visible input, select and textarea had a programmatic label.

| Form | Labelled / total |
|---|---|
| Register | 3 / 3 |
| Sign in | 2 / 2 |
| Browse filters | 3 / 3 |
| Add a Book | 5 / 5 |
| Requests | 2 / 2 |
| Profile | 3 / 3 |

My Listings and Exchanges have no input fields on their list views.

## 4. Keyboard access

| Check | Result |
|---|---|
| Tab order on Sign in | Email, Password, Sign in button, then Create an account link; logical order |
| Sign in using only the keyboard (type, Tab, type, Enter) | Worked; the Sign out control appeared |
| Add a Book fields reached with Tab | Worked (title, author, ISBN, condition, location) |
| Buttons show a visible focus indicator | Yes: a solid 3 px outline (`06b-focus-button-360.png`) |
| Inputs show a visible focus indicator | Yes: the border turns green with a soft glow (`06a-focus-input-360.png`) |

## 5. Validation errors and empty states

| Situation | What the user sees | Readable | Screenshot |
|---|---|---|---|
| Register with empty fields | Browser message "Please fill out this field." on the first required field | Yes | `03-register-empty-error-360.png` |
| Register with a non-campus email and a 5 character password | Red box: "Value error, Password must be at least 8 characters" | Yes | `04-register-invalid-error-360.png` |
| Sign in with a wrong password | "Invalid email or password." (same text for unknown email) | Yes | `05-login-wrong-password-360.png` |
| Add a Book with empty required fields | Browser message "Please fill out this field." | Yes | `11-listing-empty-error-360.png` |
| Search with no matches | "No books found. Try changing your search terms or clearing the filters." with a View All Books button | Yes | `10-search-empty-360.png` |

## 6. Observations (not failures, listed for transparency)

1. The password error begins with the server's wording "Value error," which is technical; a plain message would be friendlier.
2. Input focus is shown by a border colour change and a soft glow, which is subtler than the outline on buttons. A stronger focus ring would help low-vision users.
3. Empty required fields use the browser's native message, which is readable but is styled by the browser, not by the app.
4. Colour contrast was not measured with a tool in this run.
5. The check covered Chromium only.

## 7. Conclusion

NF-003 is met for the specified checks: no horizontal scroll at 360 px, at most four clicks for the two flows, labelled inputs on all forms, working keyboard access, and readable errors. TC-UX-01 can be recorded as Pass with the observations above.
