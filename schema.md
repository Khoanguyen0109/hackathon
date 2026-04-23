# Database Schema

## t_country

| Column           | Type    |
| ---------------- | ------- |
| **id**           | integer |
| name             | string  |
| country_iso_code | string  |

## t_station_area

| Column | Type    |
| ------ | ------- |
| **id** | integer |
| name   | string  |

## t_station

| Column              | Type     |
| ------------------- | -------- |
| **id**              | integer  |
| name                | string   |
| brand               | string   |
| created             | datetime |
| created_by          | integer  |
| updated             | datetime |
| updated_by          | integer  |
| human_readable_name | string   |
| station_area_id     | integer  |
| tsv                 | tsvector |

**Relations:**
- `station_area_id` → `t_station_area.id`

## t_station_visibility

| Column     | Type     |
| ---------- | -------- |
| **id**     | integer  |
| station_id | integer  |
| active     | boolean  |
| country_id | integer  |
| created    | datetime |
| created_by | integer  |
| updated    | datetime |
| updated_by | integer  |

**Relations:**
- `station_id` → `t_station.id`
- `country_id` → `t_country.id`

## t_equipment

| Column      | Type     |
| ----------- | -------- |
| **id**      | integer  |
| name        | string   |
| created_by  | integer  |
| created     | datetime |
| brand       | string   |
| enabled_iot | boolean  |

## t_country_equipment

| Column       | Type    |
| ------------ | ------- |
| **id**       | integer |
| equipment_id | integer |
| country_id   | integer |
| active       | boolean |
| min_quantity | integer |
| max_quantity | integer |

**Relations:**
- `equipment_id` → `t_equipment.id`
- `country_id` → `t_country.id`

## t_store

| Column                | Type    |
| --------------------- | ------- |
| **id**                | integer |
| internal_store_number | string  |
| store_status          | string  |
| active                | boolean |

## t_store_station

| Column                | Type     |
| --------------------- | -------- |
| **id**                | integer  |
| store_id              | integer  |
| quantity              | integer  |
| updated_by            | integer  |
| updated               | datetime |
| name                  | string   |
| human_readable_name   | string   |
| station_area_id       | integer  |
| station_visibility_id | integer  |
| active                | boolean  |
| deleted               | boolean  |

**Relations:**
- `store_id` → `t_store.id`
- `station_area_id` → `t_station_area.id`
- `station_visibility_id` → `t_station_visibility.id`

## t_store_task

| Column              | Type     |
| ------------------- | -------- |
| **id**              | integer  |
| store_id            | integer  |
| name                | string   |
| human_readable_name | string   |
| active              | boolean  |
| deleted             | boolean  |
| created             | datetime |
| created_by          | integer  |
| updated             | datetime |
| updated_by          | integer  |

**Relations:**
- `store_id` → `t_store.id`
