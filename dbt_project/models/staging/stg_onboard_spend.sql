with source as (
    select * from {{ source('raw', 'STG_ONBOARD_SPEND') }}
),

renamed as (
    select
        booking_id,
        guest_id,
        brand,
        sail_date::date            as sail_date,
        dining,
        spa,
        excursions,
        beverage,
        casino,
        retail,
        total_onboard_spend_usd,
        _fivetran_synced::timestamp as _fivetran_synced
    from source
)

select * from renamed