import { Component } from '@angular/core';

@Component({
    selector: 'app-layout',
    templateUrl: './layout.component.html',
    styleUrl: './layout.component.scss',
})
export class LayoutComponent {
    isCollapsed = false;

    menuItems: MenuItem[] = [
        { title: 'Dashboard', icon: 'fas fa-home', route: '/dashboard' },
        {
            title: 'Talleres',
            icon: 'fas fa-tools',
            subItems: [
                { title: 'Talleres', icon: 'fas fa-building', route: '/talleres/talleres' },
                { title: 'Grupos', icon: 'fas fa-users', route: '/talleres/grupos' },
                { title: 'Usuarios', icon: 'fas fa-user', route: '/talleres/usuarios' },
            ],
        },
        {
            title: 'Repuestos',
            icon: 'fas fa-boxes',
            subItems: [
                { title: 'Movimientos', icon: 'fas fa-exchange-alt', route: '/movimientos' },
                { title: 'Forecasting', icon: 'fas fa-chart-line', route: '/forecasting' },
                { title: 'Stock', icon: 'fas fa-boxes', route: '/repuestos/stock' },
                { title: 'Catalogo', icon: 'fas fa-book', route: '/repuestos/catalogo' },
                { title: 'Marcas', icon: 'fas fa-tags', route: '/repuestos/marcas' },
                { title: 'Modelos', icon: 'fas fa-car', route: '/repuestos/modelos' },
            ],
        },
        { title: 'Configuracion', icon: 'fas fa-gear', route: '/configuracion' },
    ];

    openSubmenus = new Set<MenuItem>();
    selectedItem?: MenuItem;

    toggleSidebar() {
        this.isCollapsed = !this.isCollapsed;
    }

    toggleSubmenu(item: MenuItem, event: Event) {
        if (!item.subItems?.length) {
            this.selectMenu(item, event);
            return;
        }
        event.preventDefault();
        if (this.openSubmenus.has(item)) {
            this.openSubmenus.delete(item);
        } else {
            this.openSubmenus.add(item);
        }
    }

    isSubmenuOpen(item: MenuItem): boolean {
        return this.openSubmenus.has(item);
    }

    selectMenu(item: MenuItem, event: Event) {
        event.preventDefault();
        this.selectedItem = item;
    }

    isActive(item: MenuItem): boolean {
        return this.selectedItem === item;
    }

    getCollapseId(title: string): string {
        return '#' + title.toLowerCase().replace(/\s+/g, '-') + '-collapse';
    }

    logout() {
        console.log('Logout');
    }
}

interface MenuItem {
    title: string;
    icon: string;
    route?: string;
    subItems?: MenuItem[];
}
