![Current Release](https://img.shields.io/github/release/PTST/DanskeBiblioteker-HomeAssistant/all.svg?style=plastic)
![Github All Releases](https://img.shields.io/github/downloads/PTST/DanskeBiblioteker-HomeAssistant/total.svg?style=plastic)

# DanskeBiblioteker-HomeAssistant
Install the integration either manually or via HACS by adding this repo as a custom repo
Add the G4S integration by following the config flow in settings/integrations in your Home Assistant instance
Login to your G4S smart alarm account with you username and password

## Example cards
### Requirements:
[lovelace-auto-entities](https://github.com/thomasloven/lovelace-auto-entities)    
[lovelace-template-entity-row](https://github.com/thomasloven/lovelace-template-entity-row)  

Reservations available for pickup:  
![image](https://github.com/user-attachments/assets/0a1977e2-0d08-49f9-9a9a-9292bdd40af1)

``` yaml
type: custom:auto-entities
card:
  type: entities
  title: Bøger klar til afhentning
filter:
  template: >-
    {% set SENSORP = 'sensor.patrick_toft_steffensen_library_reservations' -%}
    {% set SENSORA = 'sensor.anna_library_reservations' -%}
    {% set BOOKS = states[SENSORA].attributes.data
    +states[SENSORP].attributes.data %}

    {% set READY_FOR_PICKUP = BOOKS|rejectattr('pickup_deadline','none') %}

    {%- for book in READY_FOR_PICKUP|sort(attribute='days_left_for_pickup') -%}
      {%- set IMAGE = book.image_url -%}
      {%- set AUTHOR = book.author -%}
      {%- set STATE = 'Afhent senest: ' ~ book.pickup_deadline if book.pickup_deadline else book.number_in_queue -%}
      {{
            {
              'type': 'custom:template-entity-row',
              'state': STATE,
              'name': book.title|truncate(67,true,'…'),
              'secondary': AUTHOR,
              'icon': 'mdi:book-open-page-variant',
              'image': IMAGE,
            }
          }},
    {%- endfor %}
sort:
  reverse: false
```

Reservered items:  
![image](https://github.com/user-attachments/assets/6f0b8f9a-cc9f-4143-a818-2e29ceca84e1)

``` yaml
type: custom:auto-entities
card:
  type: entities
  title: Reserverede biblioteksbøger
filter:
  template: >-
    {% set SENSORP = 'sensor.patrick_toft_steffensen_library_reservations' -%}
    {% set SENSORA = 'sensor.anna_library_reservations' -%}

    {% set BOOKS = states[SENSORA].attributes.data
    +states[SENSORP].attributes.data %}

    {% set IN_QUEUE = BOOKS|selectattr('pickup_deadline','none') %}

    {%- for book in IN_QUEUE|sort(attribute='days_left_for_pickup') -%}
      {%- set IMAGE = book.image_url -%}
      {%- set AUTHOR = book.author -%}
      {%- set STATE = 'Afhent senest: ' ~ book.pickup_deadline if book.pickup_deadline else book.number_in_queue -%}
      {{
            {
              'type': 'custom:template-entity-row',
              'state': STATE,
              'name': book.title|truncate(67,true,'…'),
              'secondary': AUTHOR,
              'icon': 'mdi:book-open-page-variant',
              'image': IMAGE,
            }
          }},
    {%- endfor %}
sort:
  reverse: false
```

Loaned items:  
![image](https://github.com/user-attachments/assets/e2cdf47a-6b3f-40de-bb30-9fa50d62ed91)

``` yaml
type: custom:auto-entities
card:
  type: entities
  title: Lånte biblioteksbøger
filter:
  template: |-
    {% set SENSORP = 'sensor.patrick_toft_steffensen_library_loans' -%}
    {% set SENSORA = 'sensor.anna_library_loans' -%}
     {% set BOOKS = states[SENSORP].attributes.data + states[SENSORA].attributes.data %}
    {%- for book in BOOKS|sort(attribute='due_date') -%}
      {%- set DUEDATE = as_datetime(book.due_date) -%}
      {%- set IMAGE = book.image_url -%}
      {%- set AUTHOR = book.author -%}
      {{
            {
              'type': 'custom:template-entity-row',
              'state': time_until(DUEDATE),
              'name': book.title|truncate(67,true,'…'),
              'secondary': AUTHOR,
              'icon': 'mdi:book-open-page-variant',
              'image': IMAGE,
            }
          }},
    {%- endfor %}
sort:
  reverse: false
```

Card ideas and template by Reddit user [u/AnAmbushOfTigers](https://www.reddit.com/r/homeassistant/comments/1eonc4y/finished_setting_up_our_new_library_books_card/)
