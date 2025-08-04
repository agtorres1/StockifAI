import { AfterViewInit, Component } from '@angular/core';
declare var bootstrap: any;

@Component({
    selector: 'app-root',
    templateUrl: './app.component.html',
    styleUrl: './app.component.scss',
})
export class AppComponent implements AfterViewInit {
    title = 'stockifai-frontend';

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
