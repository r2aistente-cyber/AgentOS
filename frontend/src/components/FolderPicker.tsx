import { useCallback, useEffect, useState } from 'react'
import { listDir, type DirListing } from '../api'

interface Props {
  initialPath?: string
  onSelect: (path: string) => void
  onClose: () => void
}

// Navegador de carpetas modal. Consume GET /api/v1/hub/fs del Hub, que solo
// lista directorios (solo lectura). Empieza en el home del usuario.
export default function FolderPicker({ initialPath, onSelect, onClose }: Props) {
  const [listing, setListing] = useState<DirListing | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const load = useCallback(async (path?: string) => {
    setLoading(true)
    setError(null)
    try {
      setListing(await listDir(path))
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    // Arranca en la ruta dada, o en el home
    load(initialPath || undefined).then(() => {
      if (!initialPath) load(undefined)
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Al montar sin initialPath, la 1ª carga trae drives+home; saltamos al home.
  useEffect(() => {
    if (listing && listing.path === '' && listing.home) load(listing.home)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [listing?.path])

  const current = listing?.path || ''

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="flex max-h-[80vh] w-full max-w-lg flex-col rounded-xl border border-slate-700 bg-slate-900 shadow-2xl">
        <div className="flex items-center justify-between border-b border-slate-800 px-4 py-3">
          <h3 className="text-sm font-semibold text-slate-100">📂 Elegir carpeta</h3>
          <button onClick={onClose} className="text-slate-500 hover:text-slate-300">
            ✕
          </button>
        </div>

        {/* Ruta actual + navegación */}
        <div className="flex items-center gap-2 border-b border-slate-800 px-4 py-2">
          <button
            onClick={() => listing?.parent != null && load(listing.parent)}
            disabled={!listing?.parent}
            className="rounded px-2 py-1 text-xs text-slate-300 hover:bg-slate-800 disabled:opacity-30"
            title="Subir un nivel"
          >
            ⬆️ Subir
          </button>
          <code className="flex-1 truncate rounded bg-slate-800 px-2 py-1 text-xs text-slate-300">
            {current || '—'}
          </code>
        </div>

        {/* Unidades (Windows) */}
        {listing && listing.drives.length > 0 && (
          <div className="flex flex-wrap gap-1.5 border-b border-slate-800 px-4 py-2">
            {listing.drives.map((d) => (
              <button
                key={d}
                onClick={() => load(d)}
                className="rounded border border-slate-700 bg-slate-800 px-2 py-1 text-xs text-slate-300 hover:bg-slate-700"
              >
                💽 {d}
              </button>
            ))}
          </div>
        )}

        {/* Lista de subcarpetas */}
        <div className="min-h-[12rem] flex-1 overflow-y-auto px-2 py-2">
          {loading && <p className="px-2 py-4 text-sm text-slate-500">Cargando…</p>}
          {error && <p className="px-2 py-4 text-sm text-rose-400">{error}</p>}
          {!loading && !error && listing && listing.dirs.length === 0 && current && (
            <p className="px-2 py-4 text-sm text-slate-500">Sin subcarpetas aquí.</p>
          )}
          {!loading &&
            listing?.dirs.map((name) => {
              const sep = current.endsWith('\\') || current.endsWith('/') ? '' : '\\'
              const full = `${current}${sep}${name}`
              return (
                <button
                  key={name}
                  onClick={() => load(full)}
                  className="flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-sm text-slate-200 hover:bg-slate-800"
                >
                  <span>📁</span>
                  <span className="truncate">{name}</span>
                </button>
              )
            })}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between gap-2 border-t border-slate-800 px-4 py-3">
          <span className="truncate text-xs text-slate-500">
            El agente se instalará en esta carpeta.
          </span>
          <div className="flex gap-2">
            <button
              onClick={onClose}
              className="rounded-lg px-3 py-1.5 text-sm text-slate-400 hover:text-slate-200"
            >
              Cancelar
            </button>
            <button
              onClick={() => current && onSelect(current)}
              disabled={!current}
              className="rounded-lg bg-indigo-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-40"
            >
              Usar esta carpeta
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
