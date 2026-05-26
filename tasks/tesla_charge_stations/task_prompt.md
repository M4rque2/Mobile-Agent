# Tesla Charge Station Collection Prompt

Collect Tesla charging station information from the 特斯拉 app's charging-station page. The task is about public Tesla charger/station locations, not the Tesla online store, vehicle ordering, test drives, accessories, or product marketing pages.

Work only inside the app UI. The Tesla account is already logged in. If the app asks for a non-destructive permission required to view charging stations, allow it. Do not start charging, reserve a charger, pay, change account settings, change vehicle settings, or perform any irreversible action.

Navigation goal:
- Open 特斯拉 app or Start from the currently open 特斯拉 app.
- Find and enter the charging-station page. It may appear as the first item of the feeds, titled:"为非Tesla车辆充电", subtitled:"访问特斯拉充电网" in next line.
- if app ask for permissions for location, allow it for once.
- You should see map of charging stations, scroll down lower half of the screen should see the station list. 
- if it says there is no charge station around, try to search for a popular area name (like 'beijing', 'shanghai', 'shenzhen') etc.
- if you see the stations from station list, click it one by one to enter the station detail page.
- when inside station detail page, extration the information of the station by standard detailed in section "Data collection goal" and save the json file to local file name as the station name.
- back to station list page for next station detail

Data collection goal:
- Record every charging station that appears in the current station list/map results.
- For each station, open details when needed and collect as many of these fields as visible:
  - `name`
  - `address`
  - `distance`
  - `status`
  - `available_stalls`
  - `total_stalls`
  - `charger_types`
  - `price`
  - `hours`
  - `amenities`
  - `notes`
- If a field is not visible, use `null`. Do not invent data.
- Avoid duplicate stations. Treat stations with the same name and address as duplicates.
- Scroll the list until there are no new stations after two consecutive scrolls or the UI clearly reaches the end.

Completion:
- When all reachable stations have been collected, finish with action `answer`, not `terminate`.
- Put a single JSON object in the `text` field of the answer action.
- The JSON object must use this schema:

```json
{
  "task": "tesla_charge_stations",
  "app": "特斯拉",
  "page": "充电",
  "collection_scope": "all reachable stations in current app results",
  "station_count": 0,
  "stations": [
    {
      "name": null,
      "address": null,
      "distance": null,
      "status": null,
      "available_stalls": null,
      "total_stalls": null,
      "charger_types": [],
      "price": null,
      "hours": null,
      "amenities": [],
      "notes": null
    }
  ],
  "warnings": []
}