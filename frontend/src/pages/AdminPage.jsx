import React, { useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext'

export default function AdminPage() {
  const { authFetch } = useAuth()
  const [status, setStatus] = useState(null)

  useEffect(() => {
    let mounted = true
    async function check() {
      try {
        const data = await authFetch('/admin/only')
        if (mounted) setStatus(data)
      } catch (e) {
        if (mounted) setStatus({ error: e.message })
      }
    }
    check()
    return () => { mounted = false }
  }, [authFetch])

  return (
    <div style={{ padding: 20 }}>
      <h2>Admin Test Page</h2>
      <pre>{status ? JSON.stringify(status, null, 2) : 'Loading...'}</pre>
    </div>
  )
}
