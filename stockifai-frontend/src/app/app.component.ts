import { AfterViewInit, Component } from '@angular/core';
import { NavigationStart, Router } from '@angular/router';
import { filter } from 'rxjs';
declare var bootstrap: any;

@Component({
    selector: 'app-root',
    templateUrl: './app.component.html',
    styleUrl: './app.component.scss',
})
export class AppComponent implements AfterViewInit {
    title = 'stockifai-frontend';

    constructor(private router: Router) {
        this.router.events.pipe(filter((e) => e instanceof NavigationStart)).subscribe(() => {
            document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach((el) => {
                const instance = bootstrap.Tooltip.getInstance(el as HTMLElement);
                if (instance && (instance as any)._activeTrigger) {
                    try {
                        instance.hide();
                    } catch {}
                    try {
                        instance.dispose();
                    } catch {}
                }
            });
        });
    }

    ngAfterViewInit(): void {
        this.initializeTooltips();
    }

    initializeTooltips(): void {
        const observer = new MutationObserver(() => {
            const tooltipTriggerList = Array.from(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
            tooltipTriggerList.forEach((el: any) => {
                if (!el.getAttribute('data-bs-original-title')) {
                    new bootstrap.Tooltip(el);
                }
            });
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true,
        });

        const initialTooltips = Array.from(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        initialTooltips.forEach((el: any) => {
            new bootstrap.Tooltip(el);
        });
    }
}
