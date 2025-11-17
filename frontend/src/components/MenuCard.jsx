
import { useState } from 'react'
import '../css/MenuCard.css'

function MenuCard({ item }) {
  const [flipped, setFlipped] = useState(false)

  // Accessibility: allow toggling flip with keyboard with Enter or Space
  const handleKey = (e) => {
    if (e.key === 'Enter' || e.key === ' ') setFlipped((s) => !s)
  }

  return (
    <div
      className="menu-card"
      onClick={() => setFlipped((s) => !s)}
      role="button"
      tabIndex={0}
      onKeyDown={handleKey}
      aria-pressed={flipped}
    >
      <div className={`card-inner ${flipped ? 'is-flipped' : ''}`}>
        <div className="card-front">
          <img src={item.picpath} alt={item.name} className="menu-card-image" />
          <div className="menu-card-content">
            <h3 className="menu-card-title">{item.name}</h3>
          </div>
        </div>

        <div className="card-back">
          <div className="menu-card-back-content">
            <h3 className="menu-card-title">{item.name}</h3>
            <p className="menu-card-description">{item.description}</p>
            <p className="menu-card-cost">${item.price.toFixed(2)}</p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default MenuCard