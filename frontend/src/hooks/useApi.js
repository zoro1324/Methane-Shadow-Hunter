import { useState, useEffect, useCallback, useRef } from 'react'

/**
 * Custom hook for API data fetching with loading/error states.
 * 
 * @param {Function} fetchFn  - Async function that returns data
 * @param {Array}    deps     - Dependency array to re-trigger fetch
 * @param {*}        initial  - Initial data value (default: null)
 */
export function useApi(fetchFn, deps = [], initial = null) {
  const [data, setData] = useState(initial)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const isMounted = useRef(true)

  useEffect(() => {
    isMounted.current = true
    return () => { isMounted.current = false }
  }, [])

  const refetch = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await fetchFn()
      if (isMounted.current) setData(result)
    } catch (err) {
      console.error('API Error:', err)
      if (isMounted.current) setError(err.message || 'Failed to fetch data')
    } finally {
      if (isMounted.current) setLoading(false)
    }
  }, [fetchFn, ...deps]) // Issue #4: include fetchFn to avoid stale closure

  useEffect(() => {
    refetch()
  }, [refetch])

  return { data, loading, error, refetch, setData }
}

export default useApi
