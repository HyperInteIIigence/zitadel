import { Component, Input, OnInit } from '@angular/core';
import { AddSMSProviderTwilioRequest, UpdateSMSProviderHTTPRequest, UpdateSMSProviderTwilioRequest } from 'src/app/proto/generated/zitadel/admin_pb';
import { SMSProvider, SMSProviderConfigState } from 'src/app/proto/generated/zitadel/settings_pb';

import { MatDialog } from '@angular/material/dialog';
import { AdminService } from 'src/app/services/admin.service';
import { ToastService } from 'src/app/services/toast.service';
import { InfoSectionType } from '../../info-section/info-section.component';
import { WarnDialogComponent } from '../../warn-dialog/warn-dialog.component';
import { PolicyComponentServiceType } from '../policy-component-types.enum';
import { DialogAddSMSProviderComponent } from './dialog-add-sms-provider/dialog-add-sms-provider.component';
import { DialogEditHttpSmsProviderComponent } from './dialog-edit-http-sms-provider/dialog-edit-http-sms-provider.component';
import { DialogTestHttpSmsProviderComponent } from './dialog-test-http-sms-provider/dialog-test-http-sms-provider.component';

@Component({
  selector: 'cnsl-notification-sms-provider',
  templateUrl: './notification-sms-provider.component.html',
  styleUrls: ['./notification-sms-provider.component.scss'],
  standalone: false,
})
export class NotificationSMSProviderComponent implements OnInit {
  @Input() public serviceType!: PolicyComponentServiceType;
  public smsProviders: SMSProvider.AsObject[] = [];

  public smsProvidersLoading: boolean = false;
  public smsProvidersLoadFailed: boolean = false;

  public SMSProviderConfigState: any = SMSProviderConfigState;
  public InfoSectionType: any = InfoSectionType;

  constructor(
    private service: AdminService,
    private dialog: MatDialog,
    private toast: ToastService,
  ) {}

  ngOnInit(): void {
    this.fetchData();
  }

  private fetchData(): void {
    this.smsProvidersLoading = true;
    this.smsProvidersLoadFailed = false;
    this.service
      .listSMSProviders()
      .then((smsProviders) => {
        this.smsProvidersLoading = false;
        if (smsProviders.resultList) {
          this.smsProviders = smsProviders.resultList;
        }
      })
      .catch((error) => {
        this.smsProvidersLoading = false;
        this.smsProvidersLoadFailed = true;
        this.toast.showError(error);
      });
  }

  public editSMSProvider(): void {
    const dialogRef = this.dialog.open(DialogAddSMSProviderComponent, {
      width: '400px',
      data: {
        smsProviders: this.smsProviders,
      },
    });

    dialogRef.afterClosed().subscribe((req: AddSMSProviderTwilioRequest | UpdateSMSProviderTwilioRequest) => {
      if (req) {
        if (this.twilio) {
          this.service
            .updateSMSProviderTwilio(req as UpdateSMSProviderTwilioRequest)
            .then(() => {
              this.toast.showInfo('SETTING.SMS.TWILIO.UPDATED', true);
              this.fetchData();
            })
            .catch((error) => {
              this.toast.showError(error);
            });
        } else {
          this.service
            .addSMSProviderTwilio(req as AddSMSProviderTwilioRequest)
            .then(() => {
              this.toast.showInfo('SETTING.SMS.TWILIO.ADDED', true);
              this.fetchData();
            })
            .catch((error) => {
              this.toast.showError(error);
            });
        }
      }
    });
  }

  /**
   * The HTTP provider's endpoint is an instance-wide authentication setting.
   * Editing is restricted to the HyperSMS pilot provider and never activates it.
   */
  public editHTTPSMSProvider(provider: SMSProvider.AsObject): void {
    if (!this.isHyperSMSProvider(provider) || !provider.http || !provider.id) return;
    const dialogRef = this.dialog.open(DialogEditHttpSmsProviderComponent, {
      width: '560px',
      data: { provider },
    });
    dialogRef.afterClosed().subscribe((req?: UpdateSMSProviderHTTPRequest) => {
      if (!req || req.getId() !== provider.id) return;
      this.service
        .updateSMSProviderHTTP(req)
        .then(() => {
          this.toast.showInfo('HyperSMS HTTP provider updated');
          this.fetchData();
        })
        .catch((error) => this.toast.showError(error));
    });
  }

  /**
   * Test SMS is an independent, privileged, allowlisted relay request.
   * It does not activate the instance-wide SMS provider.
   */
  public testHTTPSMSProvider(provider: SMSProvider.AsObject): void {
    if (!this.isHyperSMSProvider(provider)) return;
    this.dialog.open(DialogTestHttpSmsProviderComponent, {
      width: '500px',
      data: { provider },
    });
  }

  /**
   * Use Twilio's same Activate/Deactivate API path. An instance-wide
   * activation requires a second explicit operator confirmation.
   */
  public toggleHTTPSMSProviderState(provider: SMSProvider.AsObject): void {
    if (!this.isHyperSMSProvider(provider) || !provider.id) return;
    if (provider.state === SMSProviderConfigState.SMS_PROVIDER_CONFIG_ACTIVE) {
      this.toggleSMSProviderState(provider.id);
      return;
    }
    if (provider.state !== SMSProviderConfigState.SMS_PROVIDER_CONFIG_INACTIVE) return;

    const ref = this.dialog.open(WarnDialogComponent, {
      width: '480px',
      data: {
        titleKey: 'Activate HyperSMS / PlainApp',
        descriptionKey: 'This changes the SMS provider for the entire ZITADEL instance, not just a pilot account. Confirm only after a successful real handset test and recovery verification.',
        cancelKey: 'ACTIONS.CANCEL',
        confirmKey: 'ACTIONS.ACTIVATE',
        confirmation: 'ACTIVATE',
        confirmationKey: 'Type ACTIVATE to confirm this instance-wide change',
      },
    });
    ref.afterClosed().subscribe((confirmed: boolean) => {
      if (!confirmed) return;
      this.service.activateSMSProvider(provider.id).then(() => {
        this.toast.showInfo('SETTING.SMS.ACTIVATED', true);
        this.fetchData();
      }).catch((error) => this.toast.showError(error));
    });
  }

  public isHyperSMSProvider(provider: SMSProvider.AsObject): boolean {
    return !!provider.http && provider.id === '400389549018054661';
  }

  public toggleSMSProviderState(id: string): void {
    const provider = this.smsProviders.find((p) => p.id === id);
    if (provider) {
      if (provider.state === SMSProviderConfigState.SMS_PROVIDER_CONFIG_ACTIVE) {
        this.service
          .deactivateSMSProvider(id)
          .then(() => {
            this.toast.showInfo('SETTING.SMS.DEACTIVATED', true);
            this.fetchData();
          })
          .catch((error) => {
            this.toast.showError(error);
          });
      } else if (provider.state === SMSProviderConfigState.SMS_PROVIDER_CONFIG_INACTIVE) {
        this.service
          .activateSMSProvider(id)
          .then(() => {
            this.toast.showInfo('SETTING.SMS.ACTIVATED', true);
            this.fetchData();
          })
          .catch((error) => {
            this.toast.showError(error);
          });
      }
    }
  }

  public removeSMSProvider(id: string): void {
    const dialogRef = this.dialog.open(WarnDialogComponent, {
      data: {
        confirmKey: 'ACTIONS.DELETE',
        cancelKey: 'ACTIONS.CANCEL',
        titleKey: 'SETTING.SMS.REMOVEPROVIDER',
        descriptionKey: 'SETTING.SMS.REMOVEPROVIDER_DESC',
      },
      width: '400px',
    });

    dialogRef.afterClosed().subscribe((resp) => {
      if (resp) {
        this.service
          .removeSMSProvider(id)
          .then(() => {
            this.toast.showInfo('SMS provider removed');
            this.fetchData();
          })
          .catch((error) => {
            this.toast.showError(error);
          });
      }
    });
  }

  public get hyperSMSProvider(): SMSProvider.AsObject | undefined {
    return this.smsProviders.find((provider) => this.isHyperSMSProvider(provider));
  }

  public get twilio(): SMSProvider.AsObject | undefined {
    return this.smsProviders.find((p) => p.twilio);
  }
}
