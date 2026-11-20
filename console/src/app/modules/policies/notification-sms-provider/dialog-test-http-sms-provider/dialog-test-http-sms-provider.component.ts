import { Component, Inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { FormControl, FormGroup, Validators } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { OAuthService } from 'angular-oauth2-oidc';
import { lastValueFrom } from 'rxjs';
import { SMSProvider } from 'src/app/proto/generated/zitadel/settings_pb';

interface TestSMSResponse {
  status: string;
  requestId?: string;
}

@Component({
  selector: 'cnsl-dialog-test-http-sms-provider',
  templateUrl: './dialog-test-http-sms-provider.component.html',
  standalone: false,
})
export class DialogTestHttpSmsProviderComponent {
  public readonly form = new FormGroup({
    number: new FormControl('', {
      nonNullable: true,
      validators: [Validators.required, Validators.pattern(/^\+[1-9][0-9]{6,14}$/)],
    }),
    body: new FormControl('HyperSMS / PlainApp configuration test', {
      nonNullable: true,
      validators: [Validators.required, Validators.maxLength(300)],
    }),
  });
  public sending = false;
  public result = '';
  public error = '';

  constructor(
    private readonly http: HttpClient,
    private readonly oauth: OAuthService,
    public readonly dialogRef: MatDialogRef<DialogTestHttpSmsProviderComponent>,
    @Inject(MAT_DIALOG_DATA) public readonly data: { provider: SMSProvider.AsObject },
  ) {}

  public async send(): Promise<void> {
    this.error = '';
    this.result = '';
    if (this.sending || this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    if (this.data.provider.id !== '400389549018054661') {
      this.error = 'Unknown SMS provider.';
      return;
    }
    const token = this.oauth.getAccessToken();
    if (!token || !this.oauth.hasValidAccessToken()) {
      this.error = 'Your ZITADEL administrator session has expired. Sign in again.';
      return;
    }
    this.sending = true;
    try {
      const response = await lastValueFrom(
        this.http.post<TestSMSResponse>(
          '/__hypersms/test',
          { providerId: this.data.provider.id, number: this.form.controls.number.value, body: this.form.controls.body.value },
          { headers: { Authorization: 'Bearer ' + token, 'Content-Type': 'application/json' } },
        ),
      );
      if (response.status === 'accepted') {
        this.result = 'PlainApp accepted the send request. This does not confirm delivery to the recipient.';
      } else if (response.status === 'delivered') {
        this.result = 'PlainApp reported a successful SMS send outcome. This is not a carrier delivery receipt.';
      } else {
        this.error = 'Unknown relay response; SMS delivery has not been confirmed.';
      }
    } catch (error: any) {
      const status = typeof error?.status === 'number' ? error.status : 0;
      this.error = status === 404
        ? 'HyperSMS test relay is not yet connected to the ZITADEL ingress.'
        : status === 401 || status === 403
          ? 'Test denied by the relay. Check administrator permission, number allowlist and authenticated ingress.'
          : status === 503
            ? 'HyperSMS relay is not ready. Verify the phone, TLS and service status.'
            : 'The SMS request failed. No successful send outcome has been confirmed.';
    } finally {
      this.sending = false;
    }
  }
}
