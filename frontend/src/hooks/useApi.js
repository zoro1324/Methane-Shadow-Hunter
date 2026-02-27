import { useState, useEffect, useCallback } from 'react'

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

  const refetch = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await fetchFn()
      setData(result)
    } catch (err) {
      console.error('API Error:', err)
      setError(err.message || 'Failed to fetch data')
    } finally {
      setLoading(false)
    }
  }, deps) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    refetch()
  }, [refetch])

  return { data, loading, error, refetch, setData }
}

export default useApi
