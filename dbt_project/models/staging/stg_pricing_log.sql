with source as (
    select * from {{ source('raw', 'STG_PRICING_LOG') }}
),

renamed as (
    select
        price_log_id,
        brand,
        itinerary_name,
        region,
        cabin_category,
        sail_date::date            as sail_date,
        price_usd,
        recorded_at::timestamp     as recorded_at,
        _fivetran_synced::timestamp as _fivetran_synced
    from source
)

select * from renamed