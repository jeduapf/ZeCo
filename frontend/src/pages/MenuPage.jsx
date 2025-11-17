import MenuCard from '../components/MenuCard.jsx';

function Menu({translations}) {
    const defaultTranslations = {
        menu_title: 'Menu'
    }
    translations = translations || defaultTranslations
    
    // TODO: I want this to come from a database or an API in the future
    const items = [
    { id: 1, name: 'Pasta', picpath: '/menu/pasta.jpg', price: 12.99, description: 'Delicious homemade pasta.' },
    { id: 2, name: 'Lasagna', picpath: '/menu/lasagna.jpg', price: 15.59, description: 'Classic Italian lasagna with rich meat sauce.' },
    { id: 3, name: 'Hot Dog', picpath: '/menu/hotdog.png', price: 5.99, description: 'Juicy hot dog with your choice of toppings.' },
    { id: 4, name: 'Feijão tropeiro', picpath: '/menu/feijao.jpg', price: 20.00, description: 'Traditional Brazilian dish with beans and sausage.' },
    ];

    return (
        <div className="menu-page">
            <h2 className="menu-page-title">{translations.menu_title}</h2>
            <div className="menu-items-container">
                {items.map((item) => (
                    <MenuCard key={item.id} item={item} />
                ))}
            </div>
        </div>
    )
}

export default Menu;