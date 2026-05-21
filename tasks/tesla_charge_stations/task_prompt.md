# Tesla Charge Station Collection Prompt

Collect Tesla charging station information from the 特斯拉 app's charging-station page. The task is about public Tesla charger/station locations, not the Tesla online store, vehicle ordering, test drives, accessories, or product marketing pages.

Work only inside the app UI. The Tesla account is already logged in. If the app asks for a non-destructive permission required to view charging stations, allow it. Do not start charging, reserve a charger, pay, change account settings, change vehicle settings, or perform any irreversible action.

Navigation goal:
- Start from the currently open 特斯拉 app.
- Ignore store/home cards such as Model Y, 立即订购, Tesla 在线商店, 体验特斯拉, 预约试驾, vehicle advertisements, accessories, or shopping pages.
- Find and enter the charging-station page. It may appear as 充电, 超级充电站, 目的地充电站, 充电地图, 地图, 地点, 能源, 补能, Charging, Supercharger, Destination Charger, or a lightning/charging pin icon depending on app language and version.
- If you see a card like `有车友问，充电比加油还方便？` or `充电竟比加油还方便` with a `查看` button, tap `查看`; this is relevant to charging stations.
- Prefer bottom-tab/navigation/menu/search controls over repeatedly scrolling marketing content.
- If you are on a marketing/store feed, look for tabs, account/home controls, menu icons, map/search icons, or a back/home navigation path that leads to charging stations.
- If a map opens first, switch to the station list or open each visible station detail from the map/list.

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
```

Use this exact action shape for the final step:

```text
Action: Return collected charging station data.
<tool_call>
{"name":"mobile_use","arguments":{"action":"answer","text":"{\"task\":\"tesla_charge_stations\",\"app\":\"特斯拉\",\"page\":\"充电\",\"collection_scope\":\"all reachable stations in current app results\",\"station_count\":0,\"stations\":[],\"warnings\":[]}"}}
</tool_call>
```
