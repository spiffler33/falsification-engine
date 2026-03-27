import { useState, useEffect, useCallback } from 'react'
import { api } from '../lib/api'

/**
 * Hook for fetching data from the API.
 * Returns { data, loading, error, refetch }.
 */
export function useApi(path, deps = []) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetch_ = useCallback(() => {
    if (!path) {
      setLoading(false)
      return
    }
    setLoading(true)
    setError(null)
    api.get(path)
      .then(setData)
      .catch(setError)
      .finally(() => setLoading(false))
  }, [path, ...deps]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    fetch_()
  }, [fetch_])

  return { data, loading, error, refetch: fetch_ }
}
