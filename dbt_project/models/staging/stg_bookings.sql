with source as (
    select * from {{ source('raw', 'STG_BOOKINGS') }}
),

renamed as (
    select
        booking_id,
        guest_id,
        brand,
        ship_name,
        itinerary_name,
        region,
        nights,
        cabin_category,
        num_guests,
        booking_date::date         as booking_date,
        sail_date::date            as sail_date,
        booking_window_days,
        cabin_price_usd,
        total_revenue_usd,
        booking_channel,
        is_cancelled::boolean      as is_cancelled,
        cancellation_date::date    as cancellation_date,
        cancellation_reason,
        loyalty_tier,
        _fivetran_synced::timestamp as _fivetran_synced
    from source
)

select * from renamed