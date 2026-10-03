-- reserve: fail if any cap would be exceeded, else charge all three and
-- remember the reservation.
-- KEYS: lane_hour, lane_day, global_hour, reserve
-- ARGV: est, lane_hour_cap, lane_day_cap, global_hour_cap, reserve_ttl
--       hour_ttl, day_ttl
-- returns 1 on success, 0 when a cap would be exceeded
local est = tonumber(ARGV[1])
local lane_hour = tonumber(redis.call('GET', KEYS[1]) or '0')
local lane_day = tonumber(redis.call('GET', KEYS[2]) or '0')
local global_hour = tonumber(redis.call('GET', KEYS[3]) or '0')
if lane_hour + est > tonumber(ARGV[2]) then return 0 end
if lane_day + est > tonumber(ARGV[3]) then return 0 end
if global_hour + est > tonumber(ARGV[4]) then return 0 end
redis.call('INCRBY', KEYS[1], est)
redis.call('EXPIRE', KEYS[1], tonumber(ARGV[6]))
redis.call('INCRBY', KEYS[2], est)
redis.call('EXPIRE', KEYS[2], tonumber(ARGV[7]))
redis.call('INCRBY', KEYS[3], est)
redis.call('EXPIRE', KEYS[3], tonumber(ARGV[6]))
redis.call('SET', KEYS[4], est, 'EX', tonumber(ARGV[5]))
return 1
