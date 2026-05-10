# TimeToScore Sharks Ice API Notes

This documents the API calls made by the Sharks Ice TimeToScore test site at:

`https://stats.sharksice.timetoscore.com/test/site.php?league=1&season=74&stat_class=1`

The calls below were captured from the site through the Chrome DevTools Protocol on May 10, 2026. JavaScript bundles were also inspected to include calls that are made after interacting with controls, such as the Standings `Special Teams` tab.

## Coverage

The crawl started from the public standings, schedule, stats, and teams pages, then followed internal `/test/*.php` links and rendered pages in the browser. The raw crawl fetched 250 internal PHP URLs and found these page templates: `site.php`, `schedule.php`, `skater-leaders.php`, `goalie-leaders.php`, `teams.php`, `team.php`, and `game.php`.

All discovered JavaScript bundles were scanned for signed `get_*` API calls. The API endpoints discovered are:

`get_divisions`, `get_game_center`, `get_goalies`, `get_leagues`, `get_roster`, `get_schedule`, `get_schedule_lite`, `get_schedule_months`, `get_skaters`, `get_special_teams_stats`, `get_standings`, `get_team_info`, `get_team_stats`, and `get_widget_config`.

## Hosts

| Host                                              | Purpose                                                      |
| ------------------------------------------------- | ------------------------------------------------------------ |
| `https://stats.sharksice.timetoscore.com/test/` | Public site pages, static assets, and server-rendered pages. |
| `https://api.sharksice.timetoscore.com/`        | Signed JSON API used by the React widgets.                   |

## Page And Bundle Map

| Site page                                                    | JavaScript bundle                        | API behavior                                                                                                           |
| ------------------------------------------------------------ | ---------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| `/test/site.php?league=1&season=74&stat_class=1`           | `/test/scorebug-assets/index.js`       | Loads theme config and a date-window schedule for the scorebug/top games strip.                                        |
| `/test/site.php?league=1&season=74&stat_class=1`           | `/test/standings-assets/index.js`      | Loads league metadata, standings widget config, standings, and special-teams stats when the Special Teams tab is used. |
| `/test/schedule.php?league=1&season=74`                    | `/test/schedule-assets/index.js`       | Loads league metadata, division/filter metadata, schedule games, schedule months, and theme config.                    |
| `/test/skater-leaders.php?league=1&season=74&stat_class=1` | `/test/skater-leaders-assets/index.js` | Loads league metadata, division/filter metadata, skater leaders, and theme config.                                     |
| `/test/goalie-leaders.php?league=1&season=74&stat_class=1` | `/test/goalie-leaders-assets/index.js` | Loads league metadata, division/filter metadata, goalie leaders, and theme config.                                     |
| `/test/teams.php?league=1&season=74`                       | None observed                            | Appears server-rendered on initial load; links to individual team pages.                                               |
| `/test/team.php?team={team_id}&season={season_id}`         | `/test/team-assets/index.js`           | Loads team info, roster, team stats, team schedule, division standings, league metadata, and widget config.            |
| `/test/game.php?game={game_id}`                            | `/test/game-assets/index.js`           | Loads game center data and theme config.                                                                               |

## API Calls

All observed API calls are HTTP `GET` requests to `https://api.sharksice.timetoscore.com/{endpoint}`. Each request includes the shared auth parameters documented later.

| Endpoint                    | Used by                                                                             | Non-auth parameters                                                                                                                                                         | Observed status                                                                                                           | What it does                                                                                                                                                                                                                                                              |
| --------------------------- | ----------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `get_widget_config`       | Scorebug, standings, schedule, skater leaders, goalie leaders, team page, game page | `widget`, optional `league_id`, optional `customer`, optional `team_id`                                                                                             | `200` for `theme`, `standings`, and `team`; `404` observed for `skater-leaders` and `goalie-leaders` config | Fetches widget configuration.`widget=theme` provides styling/theme data. `widget=standings` and `widget=team` provide layout/tab configuration. Missing widget configs appear to fall back to built-in defaults.                                                    |
| `get_schedule`            | Scorebug/top games strip and team page                                              | `league_id`, `season_id`, optional `team_id`, optional `stat_class`, optional `start`, optional `end`                                                           | `200`                                                                                                                   | Fetches games. The scorebug uses a date range. Team pages use `team_id` and season/stat filters to fetch that team's schedule.                                                                                                                                          |
| `get_leagues`             | Standings, schedule, skater leaders, goalie leaders, team page                      | Optional `league_id`                                                                                                                                                      | `200`                                                                                                                   | Fetches league metadata used to populate page controls and current league context. Initial capture used `league_id=1`.                                                                                                                                                  |
| `get_standings`           | Standings page and team page                                                        | `league_id`, optional `season_id`, optional `stat_class`, optional `level_id`, optional `conf_id`                                                                 | `200`                                                                                                                   | Fetches standings rows for the selected league, season, stat class, and optional division/level context. Team pages use this to show the team's division standings.                                                                                                       |
| `get_special_teams_stats` | Standings page Special Teams tab                                                    | `league_id`, optional `season_id`, optional `stat_class`                                                                                                              | Present in bundle; not fired during initial page load                                                                     | Fetches power-play, penalty-kill, or other special-teams standings data for the selected league, season, and stat class.                                                                                                                                                  |
| `get_divisions`           | Schedule, skater leaders, goalie leaders                                            | `league_id`, `season_id`                                                                                                                                                | `200`                                                                                                                   | Fetches division, level, conference, and/or team filter metadata for the selected league and season. Initial capture used `league_id=1`, `season_id=74`.                                                                                                              |
| `get_schedule_lite`       | Schedule page                                                                       | `league_id`, `season_id`, optional `level_id`, optional `conf_id`, optional `team_id`, optional `start`, optional `end`, optional `date`, optional `days` | `200`                                                                                                                   | Fetches schedule game rows for the schedule view. Initial capture used `league_id=1`, `season_id=74`, `date=2026-05-10`, `days=20`. The bundle maps logo paths using response `base_urls.assets` and creates scorecard links from response `base_urls.stats`. |
| `get_schedule_months`     | Schedule page                                                                       | `league_id`, `season_id`, optional `level_id`, optional `conf_id`, optional `team_id`                                                                             | `200`                                                                                                                   | Fetches the months/date buckets that have schedule data, used by schedule navigation.                                                                                                                                                                                     |
| `get_skaters`             | Skater leaders page                                                                 | `league_id`, optional `season_id`, optional `stat_class`, optional `level_id`, optional `start_date`, optional `end_date`, optional `limit`                   | `200`                                                                                                                   | Fetches skater/player leaderboard rows for the selected filters. Initial capture used `league_id=1`, `season_id=74`, `stat_class=1`, `limit=200`.                                                                                                                 |
| `get_goalies`             | Goalie leaders page                                                                 | `league_id`, optional `season_id`, optional `stat_class`, optional `level_id`, optional `start_date`, optional `end_date`, optional `limit`                   | `200`                                                                                                                   | Fetches goalie leaderboard rows for the selected filters. Initial capture used `league_id=1`, `season_id=74`, `stat_class=1`, `limit=200`.                                                                                                                        |
| `get_team_info`           | Team page                                                                           | `team_id`                                                                                                                                                                 | `200`                                                                                                                   | Fetches team identity and metadata for the selected team.                                                                                                                                                                                                                 |
| `get_roster`              | Team page                                                                           | `team_id`, optional `league_id`, optional `season_id`, optional `stat_class`                                                                                        | `200`                                                                                                                   | Fetches the team roster for the selected season/stat class.                                                                                                                                                                                                               |
| `get_team_stats`          | Team page                                                                           | `team_id`, optional `league_id`, optional `season_id`, optional `stat_class`, optional `opp_id`                                                                   | `200`                                                                                                                   | Fetches team-level statistics, optionally filtered by opponent.                                                                                                                                                                                                           |
| `get_game_center`         | Game page                                                                           | `game_id`, optional `stat_class`                                                                                                                                        | `200`                                                                                                                   | Fetches game detail/game center data for a single game, including teams, score state, and game summary data used by the game page.                                                                                                                                        |

## Initial API Traffic Captured

These are the sanitized calls observed on first load of the primary pages. `auth_timestamp` and `auth_signature` are generated per request and are redacted here.

| Page                    | Endpoint                | Status  | Sanitized query                                                                                                                                             |
| ----------------------- | ----------------------- | ------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Standings page          | `get_widget_config`   | `200` | `auth_key=web&auth_timestamp=<ts>&body_md5=d41d8cd98f00b204e9800998ecf8427e&league_id=1&widget=theme&auth_signature=<sig>`                                |
| Standings page scorebug | `get_schedule`        | `200` | `auth_key=web&auth_timestamp=<ts>&body_md5=d41d8cd98f00b204e9800998ecf8427e&end=2026-05-13&league_id=1&season_id=0&start=2026-05-07&auth_signature=<sig>` |
| Standings page          | `get_leagues`         | `200` | `auth_key=web&auth_timestamp=<ts>&body_md5=d41d8cd98f00b204e9800998ecf8427e&league_id=1&auth_signature=<sig>`                                             |
| Standings page          | `get_widget_config`   | `200` | `auth_key=web&auth_timestamp=<ts>&body_md5=d41d8cd98f00b204e9800998ecf8427e&customer=sharksice&league_id=1&widget=standings&auth_signature=<sig>`         |
| Standings page          | `get_standings`       | `200` | `auth_key=web&auth_timestamp=<ts>&body_md5=d41d8cd98f00b204e9800998ecf8427e&league_id=1&season_id=74&stat_class=1&auth_signature=<sig>`                   |
| Schedule page           | `get_widget_config`   | `200` | `auth_key=web&auth_timestamp=<ts>&body_md5=d41d8cd98f00b204e9800998ecf8427e&league_id=1&widget=theme&auth_signature=<sig>`                                |
| Schedule page           | `get_leagues`         | `200` | `auth_key=web&auth_timestamp=<ts>&body_md5=d41d8cd98f00b204e9800998ecf8427e&league_id=1&auth_signature=<sig>`                                             |
| Schedule page           | `get_divisions`       | `200` | `auth_key=web&auth_timestamp=<ts>&body_md5=d41d8cd98f00b204e9800998ecf8427e&league_id=1&season_id=74&auth_signature=<sig>`                                |
| Schedule page           | `get_schedule_lite`   | `200` | `auth_key=web&auth_timestamp=<ts>&body_md5=d41d8cd98f00b204e9800998ecf8427e&date=2026-05-10&days=20&league_id=1&season_id=74&auth_signature=<sig>`        |
| Schedule page           | `get_schedule_months` | `200` | `auth_key=web&auth_timestamp=<ts>&body_md5=d41d8cd98f00b204e9800998ecf8427e&league_id=1&season_id=74&auth_signature=<sig>`                                |
| Skater leaders page     | `get_widget_config`   | `200` | `auth_key=web&auth_timestamp=<ts>&body_md5=d41d8cd98f00b204e9800998ecf8427e&league_id=1&widget=theme&auth_signature=<sig>`                                |
| Skater leaders page     | `get_leagues`         | `200` | `auth_key=web&auth_timestamp=<ts>&body_md5=d41d8cd98f00b204e9800998ecf8427e&league_id=1&auth_signature=<sig>`                                             |
| Skater leaders page     | `get_widget_config`   | `404` | `auth_key=web&auth_timestamp=<ts>&body_md5=d41d8cd98f00b204e9800998ecf8427e&league_id=1&widget=skater-leaders&auth_signature=<sig>`                       |
| Skater leaders page     | `get_divisions`       | `200` | `auth_key=web&auth_timestamp=<ts>&body_md5=d41d8cd98f00b204e9800998ecf8427e&league_id=1&season_id=74&auth_signature=<sig>`                                |
| Skater leaders page     | `get_skaters`         | `200` | `auth_key=web&auth_timestamp=<ts>&body_md5=d41d8cd98f00b204e9800998ecf8427e&league_id=1&limit=200&season_id=74&stat_class=1&auth_signature=<sig>`         |
| Goalie leaders page     | `get_widget_config`   | `404` | `auth_key=web&auth_timestamp=<ts>&body_md5=d41d8cd98f00b204e9800998ecf8427e&league_id=1&widget=goalie-leaders&auth_signature=<sig>`                       |
| Goalie leaders page     | `get_goalies`         | `200` | `auth_key=web&auth_timestamp=<ts>&body_md5=d41d8cd98f00b204e9800998ecf8427e&league_id=1&limit=200&season_id=74&stat_class=1&auth_signature=<sig>`         |
| Team page               | `get_widget_config`   | `200` | `auth_key=web&auth_timestamp=<ts>&body_md5=d41d8cd98f00b204e9800998ecf8427e&customer=sharksice&team_id=323&widget=team&auth_signature=<sig>`              |
| Team page               | `get_team_info`       | `200` | `auth_key=web&auth_timestamp=<ts>&body_md5=d41d8cd98f00b204e9800998ecf8427e&team_id=323&auth_signature=<sig>`                                             |
| Team page               | `get_roster`          | `200` | `auth_key=web&auth_timestamp=<ts>&body_md5=d41d8cd98f00b204e9800998ecf8427e&league_id=1&season_id=74&stat_class=1&team_id=323&auth_signature=<sig>`       |
| Team page               | `get_schedule`        | `200` | `auth_key=web&auth_timestamp=<ts>&body_md5=d41d8cd98f00b204e9800998ecf8427e&league_id=1&season_id=74&stat_class=1&team_id=323&auth_signature=<sig>`       |
| Team page               | `get_standings`       | `200` | `auth_key=web&auth_timestamp=<ts>&body_md5=d41d8cd98f00b204e9800998ecf8427e&league_id=1&level_id=221&season_id=74&stat_class=1&auth_signature=<sig>`      |
| Team page               | `get_team_stats`      | `200` | `auth_key=web&auth_timestamp=<ts>&body_md5=d41d8cd98f00b204e9800998ecf8427e&league_id=1&season_id=74&stat_class=1&team_id=323&auth_signature=<sig>`       |
| Game page               | `get_game_center`     | `200` | `auth_key=web&auth_timestamp=<ts>&body_md5=d41d8cd98f00b204e9800998ecf8427e&game_id=576970&auth_signature=<sig>`                                          |

## Authentication And Signing

The API does not use a login cookie or bearer token for these public widgets. Instead, each request is signed with a shared client key and secret embedded in the page markup.

The site markup provides these values on the widget root elements:

| Attribute           | Purpose                                                                                        |
| ------------------- | ---------------------------------------------------------------------------------------------- |
| `data-api-base`   | API root URL. Observed as `https://api.sharksice.timetoscore.com/`.                          |
| `data-api-key`    | Public API key. Observed as `web`.                                                           |
| `data-api-secret` | Shared HMAC secret used by browser JavaScript to sign API requests. Redacted in this document. |

Every API request includes these common query parameters:

| Parameter          | Value                                                                                                                               |
| ------------------ | ----------------------------------------------------------------------------------------------------------------------------------- |
| `auth_key`       | Value from `data-api-key`, observed as `web`.                                                                                   |
| `auth_timestamp` | Current Unix timestamp in seconds at request time.                                                                                  |
| `body_md5`       | MD5 of the request body. For these `GET` requests the body is empty, so the value is always `d41d8cd98f00b204e9800998ecf8427e`. |
| `auth_signature` | Lowercase hex HMAC-SHA256 signature.                                                                                                |

Signing algorithm used by the bundles:

1. Start with the common auth parameters except `auth_signature`.
2. Add endpoint-specific parameters.
3. Omit parameters whose value is `null`, `undefined`, an empty string, or `-1`.
4. Sort all remaining parameter names lexicographically.
5. URL-encode keys and values with `encodeURIComponent`, then replace `%20` with `+`.
6. Join the encoded pairs with `&` to create the canonical query string.
7. Build the string to sign as `GET /{endpoint} {canonical_query}`.
8. HMAC-SHA256 sign that string using the UTF-8 bytes of `data-api-secret`.
9. Append `auth_signature={hex_signature}` to the final query string.
10. Fetch the URL with `credentials: "omit"`.

Pseudo-code:

```js
const emptyBodyMd5 = "d41d8cd98f00b204e9800998ecf8427e";

function encodeQueryValue(value) {
  return encodeURIComponent(value).replace(/%20/g, "+");
}

function canonicalQuery(params) {
  return Object.keys(params)
    .sort()
    .map((key) => `${encodeQueryValue(key)}=${encodeQueryValue(params[key])}`)
    .join("&");
}

async function signRequest({ apiBase, apiKey, apiSecret }, endpoint, params) {
  const signedParams = {
    auth_key: apiKey,
    auth_timestamp: String(Math.floor(Date.now() / 1000)),
    body_md5: emptyBodyMd5,
  };

  for (const [key, value] of Object.entries(params || {})) {
    if (value !== null && value !== undefined && value !== "" && value !== -1) {
      signedParams[key] = String(value);
    }
  }

  const query = canonicalQuery(signedParams);
  const stringToSign = `GET /${endpoint} ${query}`;
  const signature = await hmacSha256Hex(apiSecret, stringToSign);

  return `${apiBase.replace(/\/$/, "")}/${endpoint}?${query}&auth_signature=${signature}`;
}
```

Security note: because the key and signing secret are embedded in publicly served HTML and used by browser JavaScript, this mechanism should not be treated as private user authentication. It is request signing for public widget data, not a user identity system.

## Related Non-API Links

The schedule bundle creates scorecard links from returned schedule data, but these links are not API calls during initial page load:

| Link pattern                                    | Purpose                                                                     |
| ----------------------------------------------- | --------------------------------------------------------------------------- |
| `/generate-scorecard.php?game_id={game_id}`   | Scorecard PDF/page link generated from `get_schedule_lite` response data. |
| `/test/game.php?game={game_id}`               | Public game detail page linked from schedules/scorebug.                     |
| `/test/team.php?team={team_id}`               | Public team detail page linked from standings/team lists.                   |
| `/test/goalie-leaders.php?league={league_id}` | Public goalie leaderboard page linked from rendered stats navigation.       |
