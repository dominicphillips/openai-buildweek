import { useState } from 'react'

export type TechnicalViewRole = 'back' | 'left' | 'right'

export type TechnicalViewRecord = {
  id: string
  project_id: string
  design_version_id: string
  role: TechnicalViewRole
  prompt: string
  model: string
  status: 'pending' | 'running' | 'ready' | 'failed'
  output_asset_id?: string | null
  error_code?: string | null
  asset_url?: string | null
}

type TechnicalViewsProps = {
  projectId: string
  versionId: string
  views: TechnicalViewRecord[]
  onViewsChange: (updatedView: TechnicalViewRecord) => void | Promise<void>
}

const roles: Array<{ role: TechnicalViewRole; label: string }> = [
  { role: 'back', label: 'BACK' },
  { role: 'left', label: 'LEFT' },
  { role: 'right', label: 'RIGHT' },
]

export function TechnicalViews({
  projectId,
  versionId,
  views,
  onViewsChange,
}: TechnicalViewsProps) {
  const [busyRoles, setBusyRoles] = useState<Set<TechnicalViewRole>>(() => new Set())
  const [roleErrors, setRoleErrors] = useState<Partial<Record<TechnicalViewRole, string>>>({})

  const renderView = async (role: TechnicalViewRole) => {
    if (busyRoles.has(role)) return

    setBusyRoles((current) => new Set(current).add(role))
    setRoleErrors((current) => ({ ...current, [role]: undefined }))

    try {
      const response = await fetch(
        `/api/projects/${encodeURIComponent(projectId)}/versions/${encodeURIComponent(versionId)}/technical-views/${role}`,
        {
          method: 'POST',
          headers: { Accept: 'application/json' },
        },
      )
      const body = (await response.json()) as TechnicalViewRecord & { detail?: string }
      if (!response.ok) throw new Error(body.detail || 'That view did not finish.')

      await onViewsChange(body)
      if (body.status !== 'ready' || !body.asset_url) {
        throw new Error('That view did not finish. Try again.')
      }
    } catch (error) {
      setRoleErrors((current) => ({
        ...current,
        [role]: error instanceof Error ? error.message : 'That view did not finish. Try again.',
      }))
    } finally {
      setBusyRoles((current) => {
        const next = new Set(current)
        next.delete(role)
        return next
      })
    }
  }

  return (
    <section className="technical-views" aria-labelledby="technical-views-title">
      <header className="technical-views__header">
        <h2 id="technical-views-title">TECHNICAL VIEWS</h2>
      </header>

      <div className="technical-views__grid">
        {roles.map(({ role, label }) => {
          const view = views.find(
            (candidate) =>
              candidate.design_version_id === versionId && candidate.role === role,
          )
          const working = busyRoles.has(role) || view?.status === 'running'
          const ready = view?.status === 'ready' && Boolean(view.asset_url)
          const failed = view?.status === 'failed' || (view?.status === 'ready' && !view.asset_url)
          const error = roleErrors[role]

          return (
            <article
              key={role}
              className={`technical-views__card technical-views__card--${ready ? 'ready' : working ? 'working' : failed ? 'failed' : 'pending'}`}
              aria-busy={working}
            >
              <h3 className="technical-views__label">{label}</h3>

              <div className="technical-views__frame">
                {ready && view?.asset_url ? (
                  <img
                    className="technical-views__image"
                    src={view.asset_url}
                    alt={`${label.toLowerCase()} view of the current garment version`}
                    draggable={false}
                  />
                ) : working ? (
                  <div className="technical-views__status" role="status" aria-live="polite">
                    <span className="loading-spinner" aria-hidden="true" />
                    <span>WORKING</span>
                  </div>
                ) : (
                  <button
                    type="button"
                    className="technical-views__action"
                    onClick={() => void renderView(role)}
                  >
                    {failed ? 'RETRY' : 'RENDER'}
                  </button>
                )}
              </div>

              {error && (
                <p className="technical-views__error" role="alert">
                  {error}
                </p>
              )}
            </article>
          )
        })}
      </div>
    </section>
  )
}
