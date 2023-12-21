package main

import (
	"fmt"
	"log"
	"os"
	"sync"

	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/awserr"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/ec2"
	"github.com/aws/aws-sdk-go/service/servicequotas"
)

func getQuotaCode(sess *session.Session) string {
	sqSvc := servicequotas.New(sess)
	input := &servicequotas.ListServiceQuotasInput{
		ServiceCode: aws.String("ec2"),
	}

	for {
		output, err := sqSvc.ListServiceQuotas(input)
		if err != nil {
			log.Println("Error getting quota code:", err)
			os.Exit(1)
		}

		for _, quota := range output.Quotas {
			if *quota.QuotaName == "Public AMIs" {
				return *quota.QuotaCode
			}
		}

		if output.NextToken == nil {
			break
		}
		input.NextToken = output.NextToken
	}
	log.Println("Quota code not found")
	os.Exit(1)
	return ""
}

func getRegions(ec2Svc *ec2.EC2) ([]*string, error) {
	input := &ec2.DescribeRegionsInput{}

	output, err := ec2Svc.DescribeRegions(input)
	if err != nil {
		return nil, err
	}

	var regions []*string
	for _, region := range output.Regions {
		regions = append(regions, region.RegionName)
	}

	return regions, nil
}

type QuotaInfo struct {
	CurrentQuota float64
	DesiredValue float64
	Status       string
	CaseId       string
}

func getQuotaInfo(sqSvc *servicequotas.ServiceQuotas, quotaCode string, region string) *QuotaInfo {
	input := &servicequotas.GetServiceQuotaInput{
		ServiceCode: aws.String("ec2"),
		QuotaCode:   aws.String(quotaCode),
	}

	output, err := sqSvc.GetServiceQuota(input)
	if err != nil {
		if awsErr, ok := err.(awserr.Error); ok {
			if message := awsErr.Code(); message == "UnknownOperationException" {
				log.Printf("[sdk] Region %s does not appear to support Service Quotas: %v", region, message)
				return nil
			}
			log.Fatalf("[sdk] Error getting quota info for %s: %v\n", region, awsErr)
		}
	}

	currentValue := *output.Quota.Value
	requestOutput, err := sqSvc.ListRequestedServiceQuotaChangeHistoryByQuota(&servicequotas.ListRequestedServiceQuotaChangeHistoryByQuotaInput{
		ServiceCode: aws.String("ec2"),
		QuotaCode:   aws.String(quotaCode),
	})

	if err != nil {
		log.Println("Error getting request info:", err)
		os.Exit(1)
	}
	var desiredValue float64
	var status string
	var caseId string
	if len(requestOutput.RequestedQuotas) > 0 {
		lastQuota := requestOutput.RequestedQuotas[len(requestOutput.RequestedQuotas)-1]
		desiredValue = *lastQuota.DesiredValue
		status = *lastQuota.Status
		switch {
		case status == "PENDING":
			caseId = "N/A"
		case status == "APPROVED":
			caseId = "APPROVED"
		case lastQuota.CaseId == nil:
			panic("Unhandled case status. Please report this")
		default:
			caseId = *lastQuota.CaseId
		}
	}
	return &QuotaInfo{currentValue, desiredValue, status, caseId}
}

func listQuotas(sess *session.Session, quotaCode string, regions []*string) {
	fmt.Println("Region\tQuota\tDesired\tStatus\tCaseId")

	var wg sync.WaitGroup
	wg.Add(len(regions))

	for _, region := range regions {
		go func(region string) {
			defer wg.Done()
			regionSqSvc := servicequotas.New(sess, &aws.Config{Region: aws.String(region)})
			quotaInfo := getQuotaInfo(regionSqSvc, quotaCode, region)
			if quotaInfo != nil {
				fmt.Printf("%s\t%.0f\t%.0f\t%s\t%s\n", region, quotaInfo.CurrentQuota, quotaInfo.DesiredValue, quotaInfo.Status, quotaInfo.CaseId)
			}
		}(aws.StringValue(region))
	}
	wg.Wait()
}

func requestQuotaIncrease(sess *session.Session, quotaCode string, regions []*string, quota float64) {
	var wg sync.WaitGroup
	wg.Add(len(regions))

	for _, region := range regions {
		go func(region string) {
			defer wg.Done()
			regionSqSvc := servicequotas.New(sess, &aws.Config{Region: aws.String(region)})
			quotaInfo := getQuotaInfo(regionSqSvc, quotaCode, region)
			if quotaInfo.CurrentQuota >= quota {
				fmt.Printf("Quota for Public AMIs in region %s is already set to %.0f, skipping request.\n", region, quotaInfo.CurrentQuota)
			} else {
				input := &servicequotas.RequestServiceQuotaIncreaseInput{
					ServiceCode:  aws.String("ec2"),
					QuotaCode:    aws.String(quotaCode),
					DesiredValue: aws.Float64(quota),
				}
				output, err := regionSqSvc.RequestServiceQuotaIncrease(input)
				if err != nil {
					fmt.Println("Error requesting quota increase:", err)
					os.Exit(1)
				}
				fmt.Printf("Successfully submitted request with ID: %s\n", aws.StringValue(output.RequestedQuota.Id))
			}
		}(*region)
	}
	wg.Wait()
}

func main() {
	// Create session
	sess := session.Must(session.NewSessionWithOptions(session.Options{
		SharedConfigState: session.SharedConfigEnable,
	}))

	// Create EC2 client
	ec2Svc := ec2.New(sess, &aws.Config{Region: aws.String("us-east-1")})

	// Get the quota code for Public AMIs once
	quotaCode := getQuotaCode(sess)

	// Get all regions
	regions, err := getRegions(ec2Svc)
	if err != nil {
		log.Println("Error getting regions:", err)
		os.Exit(1)
	}

	// List quotas for all regions
	listQuotas(sess, quotaCode, regions)

	// Request quota increase for all regions
	//requestQuotaIncrease(sess, quotaCode, regions, 50)
}
